from collections import Counter

import respx
from httpx import Response

from app.core.limiter import used as window_used
from app.core.state import MemoryStateBackend, reset_state
from app.gateway.engine import apply_strategy, ResolvedCandidate
from app.models.database import CredentialRow


def _cred(cid: str, name: str, weight=100, priority=1, latency=800, success=1.0, rpm=120):
    row = CredentialRow(
        id=cid,
        name=name,
        provider_id="p",
        weight=weight,
        priority=priority,
        avg_latency_ms=latency,
        rpm_limit=rpm,
        status="healthy",
        enabled=True,
    )
    row.success_count = int(success * 10)
    row.fail_count = int((1 - success) * 10)
    return ResolvedCandidate(
        credential=row,
        provider_id="p",
        provider_name=name,
        upstream_model="m",
        priority=priority,
        weight=weight,
        latency=latency,
        success_rate=success,
        quota_remaining=1.0,
        rpm_remaining=rpm,
        status="healthy",
    )


def test_smooth_wrr_distribution():
    reset_state(MemoryStateBackend())
    cands = [_cred("a", "A", 5), _cred("b", "B", 3), _cred("c", "C", 2)]
    counts = Counter()
    last = None
    same = 0
    for _ in range(1000):
        ordered = apply_strategy(list(cands), "weighted_round_robin", "vm-wrr")
        pick = ordered[0].credential.id
        counts[pick] += 1
        if pick == last:
            same += 1
        last = pick
    assert 430 <= counts["a"] <= 570
    assert 230 <= counts["b"] <= 370
    assert 140 <= counts["c"] <= 260
    assert same < 400


def test_least_latency_order():
    cands = [_cred("slow", "S", latency=900), _cred("fast", "F", latency=120)]
    ordered = apply_strategy(cands, "least_latency", "x")
    assert ordered[0].credential.id == "fast"


def test_production_weak_secret_rejection(monkeypatch):
    from app.core.config import get_settings
    from app.core.security_boot import assert_production_secrets

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("GATEWAY_ADMIN_API_KEY", "short")
    monkeypatch.setenv("GATEWAY_SECRET_KEY", "short")
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", "")
    get_settings.cache_clear()
    try:
        raised = False
        try:
            assert_production_secrets()
        except SystemExit:
            raised = True
        assert raised
    finally:
        get_settings.cache_clear()


def test_ssrf_blocks_private(monkeypatch):
    from app.core.config import get_settings
    from app.core.ssrf import validate_upstream_url

    monkeypatch.setenv("ALLOW_LOCAL_UPSTREAM", "false")
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()
    try:
        try:
            validate_upstream_url("http://127.0.0.1:11434", "openai_compatible")
            assert False, "expected reject"
        except ValueError:
            pass
        validate_upstream_url("http://127.0.0.1:11434", "ollama")
        validate_upstream_url("https://api.openai.com/v1", "openai_compatible")
        try:
            validate_upstream_url("file:///etc/passwd", "openai_compatible")
            assert False
        except ValueError:
            pass
    finally:
        get_settings.cache_clear()


def create_n_creds(client, admin, n=4):
    p = client.post("/admin/providers", headers=admin, json={"descriptorId": "custom-openai", "name": "Lab", "baseUrl": "https://api.example.com/v1"})
    pid = p.json()["id"]
    ids = []
    for i in range(n):
        c = client.post(
            "/admin/credentials",
            headers=admin,
            json={"providerId": pid, "name": f"K{i}", "extra": {"apiKey": f"k{i}", "baseUrl": "https://api.example.com/v1"}, "priority": i + 1},
        )
        ids.append(c.json()["id"])
    secret = client.post("/admin/api-keys", headers=admin, json={"name": "cli", "allowedVirtualModels": []}).json()["secret"]
    return pid, ids, secret


@respx.mock
def test_credential_rpm_not_counted_on_scan(client, admin):
    pid, ids, secret = create_n_creds(client, admin, 4)
    respx.post("https://api.example.com/v1/chat/completions").mock(
        return_value=Response(200, json={"choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})
    )
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {secret}"},
        json={"model": "foo", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 200
    used = [window_used(f"cred-rpm:{cid}") for cid in ids]
    assert used[0] == 1
    assert used[1:] == [0, 0, 0]


@respx.mock
def test_api_key_tpm(client, admin):
    from tests.test_gateway import create_stack

    _pid, _cid, _secret = create_stack(client, admin)
    k = client.post("/admin/api-keys", headers=admin, json={"name": "tiny-tpm", "allowedVirtualModels": [], "tpmLimit": 10, "rpmLimit": 1000})
    secret = k.json()["secret"]
    respx.post("https://api.example.com/v1/chat/completions").mock(
        return_value=Response(200, json={"choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})
    )
    h = {"Authorization": f"Bearer {secret}"}
    a = client.post("/v1/chat/completions", headers=h, json={"model": "foo", "max_tokens": 8, "messages": [{"role": "user", "content": "hi"}]})
    b = client.post("/v1/chat/completions", headers=h, json={"model": "foo", "max_tokens": 8, "messages": [{"role": "user", "content": "hi"}]})
    assert a.status_code == 200
    assert b.status_code == 429
    assert b.json()["error"]["code"] == "tpm_exceeded"


@respx.mock
def test_daily_request_limit(client, admin):
    from tests.test_gateway import create_stack

    create_stack(client, admin)
    k = client.post(
        "/admin/api-keys",
        headers=admin,
        json={"name": "daily", "allowedVirtualModels": [], "dailyRequestLimit": 1, "rpmLimit": 1000, "tpmLimit": 100000},
    )
    secret = k.json()["secret"]
    respx.post("https://api.example.com/v1/chat/completions").mock(
        return_value=Response(200, json={"choices": [{"message": {"content": "ok"}}], "usage": {}})
    )
    h = {"Authorization": f"Bearer {secret}"}
    a = client.post("/v1/chat/completions", headers=h, json={"model": "foo", "messages": [{"role": "user", "content": "hi"}]})
    b = client.post("/v1/chat/completions", headers=h, json={"model": "foo", "messages": [{"role": "user", "content": "hi"}]})
    assert a.status_code == 200
    assert b.status_code == 429
    assert b.json()["error"]["code"] == "daily_request_exceeded"


def test_monthly_budget_reset():
    from app.gateway.engine import reset_monthly_key
    from app.models.database import ApiKeyRow

    row = ApiKeyRow(id="k", name="n", key_hash="h", key_prefix="sk", monthly_spend=12, stats_month="1999-01")
    reset_monthly_key(row)
    assert row.monthly_spend == 0
    assert row.stats_month


def test_credential_daily_recovery():
    from app.gateway.engine import reset_daily_credential, QUOTA_DAILY

    row = CredentialRow(id="c", name="n", provider_id="p", status=QUOTA_DAILY, stats_day="1999-01-01", requests_today=99)
    reset_daily_credential(row)
    assert row.requests_today == 0
    assert row.status == "healthy"


@respx.mock
def test_virtual_least_latency(client, admin):
    p = client.post("/admin/providers", headers=admin, json={"descriptorId": "custom-openai", "name": "Lab", "baseUrl": "https://slow.example/v1"})
    pid = p.json()["id"]
    a = client.post("/admin/credentials", headers=admin, json={"providerId": pid, "name": "slow", "extra": {"apiKey": "a", "baseUrl": "https://slow.example/v1"}})
    b = client.post("/admin/credentials", headers=admin, json={"providerId": pid, "name": "fast", "extra": {"apiKey": "b", "baseUrl": "https://fast.example/v1"}})
    from app.core.database import SessionLocal
    from app.models.database import CredentialRow

    s = SessionLocal()
    try:
        sa = s.get(CredentialRow, a.json()["id"])
        sb = s.get(CredentialRow, b.json()["id"])
        sa.avg_latency_ms = 900
        sb.avg_latency_ms = 80
        s.commit()
    finally:
        s.close()
    secret = client.post("/admin/api-keys", headers=admin, json={"name": "k", "allowedVirtualModels": []}).json()["secret"]
    vm = client.post(
        "/admin/virtual-models",
        headers=admin,
        json={
            "slug": "fastest",
            "strategy": "least_latency",
            "candidates": [
                {"credentialId": a.json()["id"], "modelId": "m", "priority": 1, "weight": 100},
                {"credentialId": b.json()["id"], "modelId": "m", "priority": 2, "weight": 100},
            ],
        },
    )
    assert vm.status_code == 200
    respx.post("https://fast.example/v1/chat/completions").mock(
        return_value=Response(200, json={"choices": [{"message": {"content": "fast"}}], "usage": {}})
    )
    respx.post("https://slow.example/v1/chat/completions").mock(
        return_value=Response(200, json={"choices": [{"message": {"content": "slow"}}], "usage": {}})
    )
    chat = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {secret}"},
        json={"model": "fastest", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert chat.status_code == 200
    assert chat.json()["choices"][0]["message"]["content"] == "fast"


@respx.mock
def test_streaming_pending_and_complete(client, admin):
    from tests.test_gateway import create_stack

    _pid, _cid, secret = create_stack(client, admin)

    async def sse():
        yield b'data: {"choices":[{"delta":{"content":"hi"}}]}\n\n'
        yield b"data: [DONE]\n\n"

    respx.post("https://api.example.com/v1/chat/completions").mock(return_value=Response(200, stream=sse()))
    with client.stream(
        "POST",
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {secret}"},
        json={"model": "foo", "stream": True, "messages": [{"role": "user", "content": "hi"}]},
    ) as r:
        assert r.status_code == 200
        "".join(r.iter_text())
    logs = client.get("/admin/requests", headers=admin).json()
    assert logs
    assert logs[0]["requestStatus"] in {"ok", "streaming", "connecting"}
    assert logs[0]["stream"] is True


@respx.mock
def test_streaming_error(client, admin):
    from tests.test_gateway import create_stack

    create_stack(client, admin)
    secret = client.post("/admin/api-keys", headers=admin, json={"name": "e", "allowedVirtualModels": []}).json()["secret"]
    respx.post("https://api.example.com/v1/chat/completions").mock(return_value=Response(500, json={"error": "x"}))
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {secret}"},
        json={"model": "foo", "stream": True, "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code in (500, 502)
    logs = client.get("/admin/requests", headers=admin).json()
    assert logs[0]["requestStatus"] == "error"


@respx.mock
def test_native_responses_fallback(client, admin):
    from tests.test_gateway import create_stack

    create_stack(client, admin)
    secret = client.post("/admin/api-keys", headers=admin, json={"name": "r", "allowedVirtualModels": []}).json()["secret"]
    respx.post("https://api.example.com/v1/responses").mock(return_value=Response(404, json={"error": "no"}))
    respx.post("https://api.example.com/v1/chat/completions").mock(
        return_value=Response(200, json={"choices": [{"message": {"content": "via-chat"}}], "usage": {}})
    )
    r = client.post("/v1/responses", headers={"Authorization": f"Bearer {secret}"}, json={"model": "foo", "input": "hi"})
    assert r.status_code == 200
    assert "via-chat" in str(r.json())


def test_model_pricing_crud(client, admin):
    created = client.post(
        "/admin/model-pricing",
        headers=admin,
        json={"provider": "lab", "model": "gpt-test", "inputPer1M": 1.5, "outputPer1M": 6, "reasoningPer1M": 0.2},
    )
    assert created.status_code == 200
    pid = created.json()["id"]
    listed = client.get("/admin/model-pricing", headers=admin).json()
    assert any(x["id"] == pid for x in listed)
    patched = client.patch(f"/admin/model-pricing/{pid}", headers=admin, json={"outputPer1M": 7})
    assert patched.json()["outputPer1M"] == 7
    deleted = client.delete(f"/admin/model-pricing/{pid}", headers=admin)
    assert deleted.json()["ok"] is True


@respx.mock
def test_cost_aggregation(client, admin):
    from tests.test_gateway import create_stack

    create_stack(client, admin)
    client.post(
        "/admin/model-pricing",
        headers=admin,
        json={"provider": "lab", "model": "gpt-test", "inputPer1M": 1000000, "outputPer1M": 1000000},
    )
    secret = client.post("/admin/api-keys", headers=admin, json={"name": "c", "allowedVirtualModels": []}).json()["secret"]
    respx.post("https://api.example.com/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={"model": "gpt-test", "choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": 2, "completion_tokens": 2, "total_tokens": 4}},
        )
    )
    client.post("/v1/chat/completions", headers={"Authorization": f"Bearer {secret}"}, json={"model": "gpt-test", "messages": [{"role": "user", "content": "hi"}]})
    usage = client.get("/admin/usage", headers=admin).json()
    assert usage["estimatedCost"] > 0
    models = client.get("/admin/usage/models", headers=admin).json()
    assert models


def test_memory_peek_does_not_consume():
    b = MemoryStateBackend()
    assert b.sliding_window_peek("k", 2)
    assert b.sliding_window_used("k") == 0
    assert b.sliding_window_allow("k", 2)
    assert b.sliding_window_used("k") == 1
    assert b.next_round_robin("rr", 3) == 0
    assert b.next_round_robin("rr", 3) == 1


@respx.mock
def test_credential_tpm(client, admin):
    p = client.post("/admin/providers", headers=admin, json={"descriptorId": "custom-openai", "name": "Lab", "baseUrl": "https://api.example.com/v1"})
    pid = p.json()["id"]
    c = client.post(
        "/admin/credentials",
        headers=admin,
        json={"providerId": pid, "name": "tiny", "extra": {"apiKey": "a", "baseUrl": "https://api.example.com/v1"}},
    )
    from app.core.database import SessionLocal
    from app.models.database import CredentialRow

    s = SessionLocal()
    try:
        row = s.get(CredentialRow, c.json()["id"])
        row.tpm_limit = 10
        s.commit()
    finally:
        s.close()
    secret = client.post("/admin/api-keys", headers=admin, json={"name": "k", "allowedVirtualModels": [], "rpmLimit": 1000, "tpmLimit": 1000000}).json()["secret"]
    respx.post("https://api.example.com/v1/chat/completions").mock(
        return_value=Response(200, json={"choices": [{"message": {"content": "ok"}}], "usage": {}})
    )
    h = {"Authorization": f"Bearer {secret}"}
    a = client.post("/v1/chat/completions", headers=h, json={"model": "foo", "max_tokens": 8, "messages": [{"role": "user", "content": "hi"}]})
    b = client.post("/v1/chat/completions", headers=h, json={"model": "foo", "max_tokens": 8, "messages": [{"role": "user", "content": "hi"}]})
    assert a.status_code == 200
    assert b.status_code in (429, 404)
    if b.status_code == 429:
        assert b.json()["error"]["code"] in {"all_credentials_quota_exhausted", "tpm_exceeded"}


def test_admin_health_state_backend(client, admin):
    h = client.get("/admin/health", headers=admin)
    assert h.status_code == 200
    body = h.json()
    assert body["stateBackend"] in {"memory", "redis"}
    ids = [c["id"] for c in body["components"]]
    assert "redis" in ids
    assert "state" in ids
