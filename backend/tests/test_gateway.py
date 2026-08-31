import json

import respx
from httpx import Response


def create_stack(client, admin, base_url="https://api.example.com/v1"):
    p = client.post(
        "/admin/providers",
        headers=admin,
        json={"descriptorId": "custom-openai", "name": "Lab", "baseUrl": base_url},
    )
    assert p.status_code == 200, p.text
    pid = p.json()["id"]
    c = client.post(
        "/admin/credentials",
        headers=admin,
        json={
            "providerId": pid,
            "name": "Key A",
            "authType": "api_key",
            "extra": {"apiKey": "sk-test", "baseUrl": base_url},
        },
    )
    assert c.status_code == 200, c.text
    k = client.post("/admin/api-keys", headers=admin, json={"name": "cli", "allowedVirtualModels": []})
    assert k.status_code == 200, k.text
    secret = k.json()["secret"]
    assert secret.startswith("sk-gw-")
    return pid, c.json()["id"], secret


def test_admin_auth(client):
    r = client.get("/admin/providers")
    assert r.status_code == 401


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@respx.mock
def test_models_and_chat(client, admin):
    pid, _cid, secret = create_stack(client, admin)
    respx.get("https://api.example.com/v1/models").mock(
        return_value=Response(200, json={"data": [{"id": "gpt-test"}]})
    )
    sync = client.post(f"/admin/providers/{pid}/sync-models", headers=admin)
    assert sync.status_code == 200
    assert sync.json()["synced"] == 1

    gw = {"Authorization": f"Bearer {secret}"}
    models = client.get("/v1/models", headers=gw)
    assert models.status_code == 200
    ids = [m["id"] for m in models.json()["data"]]
    assert "gpt-test" in ids

    respx.post("https://api.example.com/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={
                "id": "chat1",
                "model": "gpt-test",
                "choices": [{"message": {"role": "assistant", "content": "hello"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4},
            },
        )
    )
    chat = client.post(
        "/v1/chat/completions",
        headers=gw,
        json={"model": "gpt-test", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert chat.status_code == 200
    assert chat.json()["choices"][0]["message"]["content"] == "hello"
    logs = client.get("/admin/requests", headers=admin)
    assert logs.status_code == 200
    assert len(logs.json()) >= 1
    usage = client.get("/admin/usage", headers=admin)
    assert usage.json()["requestsToday"] >= 1


def test_invalid_key(client):
    r = client.get("/v1/models", headers={"Authorization": "Bearer sk-gw-nope"})
    assert r.status_code == 401


def test_invalid_model_no_credential(client, admin):
    k = client.post("/admin/api-keys", headers=admin, json={"name": "x", "allowedVirtualModels": []})
    secret = k.json()["secret"]
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {secret}"},
        json={"model": "missing", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 404


@respx.mock
def test_virtual_model(client, admin):
    pid, cid, secret = create_stack(client, admin)
    respx.get("https://api.example.com/v1/models").mock(return_value=Response(200, json={"data": [{"id": "gpt-test"}]}))
    client.post(f"/admin/providers/{pid}/sync-models", headers=admin)
    models = client.get("/admin/models", headers=admin).json()
    mid = models[0]["id"]
    vm = client.post(
        "/admin/virtual-models",
        headers=admin,
        json={
            "slug": "coding",
            "strategy": "failover",
            "candidates": [{"modelId": mid, "credentialId": cid, "priority": 1, "weight": 100}],
        },
    )
    assert vm.status_code == 200, vm.text
    respx.post("https://api.example.com/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}], "model": "gpt-test", "usage": {}},
        )
    )
    chat = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {secret}"},
        json={"model": "coding", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert chat.status_code == 200


@respx.mock
def test_failover_429(client, admin):
    p = client.post("/admin/providers", headers=admin, json={"descriptorId": "custom-openai", "name": "Lab", "baseUrl": "https://a.example/v1"})
    pid = p.json()["id"]
    a = client.post(
        "/admin/credentials",
        headers=admin,
        json={"providerId": pid, "name": "A", "extra": {"apiKey": "a", "baseUrl": "https://a.example/v1"}, "priority": 1},
    )
    b = client.post(
        "/admin/credentials",
        headers=admin,
        json={"providerId": pid, "name": "B", "extra": {"apiKey": "b", "baseUrl": "https://b.example/v1"}, "priority": 2},
    )
    assert a.status_code == 200 and b.status_code == 200
    k = client.post("/admin/api-keys", headers=admin, json={"name": "k", "allowedVirtualModels": []})
    secret = k.json()["secret"]
    respx.post("https://a.example/v1/chat/completions").mock(return_value=Response(429, json={"error": "rate"}))
    respx.post("https://b.example/v1/chat/completions").mock(
        return_value=Response(200, json={"choices": [{"message": {"content": "from-b"}}], "usage": {}})
    )
    chat = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {secret}"},
        json={"model": "foo", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert chat.status_code == 200
    assert chat.json()["choices"][0]["message"]["content"] == "from-b"
    logs = client.get("/admin/requests", headers=admin).json()
    assert logs[0]["fallbackCount"] >= 1


@respx.mock
def test_timeout_failover(client, admin):
    import httpx

    p = client.post("/admin/providers", headers=admin, json={"descriptorId": "custom-openai", "name": "Lab", "baseUrl": "https://a.example/v1"})
    pid = p.json()["id"]
    client.post("/admin/credentials", headers=admin, json={"providerId": pid, "name": "A", "extra": {"apiKey": "a", "baseUrl": "https://a.example/v1"}, "priority": 1})
    client.post("/admin/credentials", headers=admin, json={"providerId": pid, "name": "B", "extra": {"apiKey": "b", "baseUrl": "https://b.example/v1"}, "priority": 2})
    secret = client.post("/admin/api-keys", headers=admin, json={"name": "k", "allowedVirtualModels": []}).json()["secret"]
    respx.post("https://a.example/v1/chat/completions").mock(side_effect=httpx.TimeoutException("t"))
    respx.post("https://b.example/v1/chat/completions").mock(
        return_value=Response(200, json={"choices": [{"message": {"content": "ok"}}], "usage": {}})
    )
    chat = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {secret}"},
        json={"model": "foo", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert chat.status_code == 200


@respx.mock
def test_circuit_breaker(client, admin):
    p = client.post("/admin/providers", headers=admin, json={"descriptorId": "custom-openai", "name": "Lab", "baseUrl": "https://a.example/v1"})
    pid = p.json()["id"]
    client.post("/admin/credentials", headers=admin, json={"providerId": pid, "name": "A", "extra": {"apiKey": "a", "baseUrl": "https://a.example/v1"}})
    secret = client.post("/admin/api-keys", headers=admin, json={"name": "k", "allowedVirtualModels": []}).json()["secret"]
    respx.post("https://a.example/v1/chat/completions").mock(return_value=Response(500, json={"error": "x"}))
    for _ in range(5):
        client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {secret}"},
            json={"model": "foo", "messages": [{"role": "user", "content": "hi"}]},
        )
    creds = client.get("/admin/credentials", headers=admin).json()
    assert creds[0]["status"] == "circuit_open"
    cbs = client.get("/admin/circuit-breakers", headers=admin).json()
    assert len(cbs) == 1


@respx.mock
def test_streaming(client, admin):
    pid, _cid, secret = create_stack(client, admin)

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
        text = "".join(r.iter_text())
        assert "[DONE]" in text or "hi" in text


def test_capabilities(client, admin):
    r = client.get("/admin/capabilities", headers=admin)
    assert r.status_code == 200
    body = r.json()
    assert "priority" in body["strategies"]
    assert "least_load" not in body["strategies"]
    assert "openai_compatible" in body["adapters"]


def test_rpm_limit(client, admin):
    pid, _cid, secret = create_stack(client, admin)
    keys = client.get("/admin/api-keys", headers=admin).json()
    kid = keys[0]["id"]
    # patch rpm via creating a tiny-limit key
    k = client.post("/admin/api-keys", headers=admin, json={"name": "tiny", "allowedVirtualModels": [], "rpmLimit": 1})
    secret = k.json()["secret"]
    import respx
    from httpx import Response

    with respx.mock:
        respx.post("https://api.example.com/v1/chat/completions").mock(
            return_value=Response(200, json={"choices": [{"message": {"content": "ok"}}], "usage": {}})
        )
        h = {"Authorization": f"Bearer {secret}"}
        a = client.post("/v1/chat/completions", headers=h, json={"model": "foo", "messages": [{"role": "user", "content": "hi"}]})
        b = client.post("/v1/chat/completions", headers=h, json={"model": "foo", "messages": [{"role": "user", "content": "hi"}]})
    assert a.status_code == 200
    assert b.status_code == 429
    assert b.json()["error"]["code"] == "rpm_exceeded"


@respx.mock
def test_responses_failover(client, admin):
    p = client.post("/admin/providers", headers=admin, json={"descriptorId": "custom-openai", "name": "Lab", "baseUrl": "https://a.example/v1"})
    pid = p.json()["id"]
    client.post("/admin/credentials", headers=admin, json={"providerId": pid, "name": "A", "extra": {"apiKey": "a", "baseUrl": "https://a.example/v1"}, "priority": 1})
    client.post("/admin/credentials", headers=admin, json={"providerId": pid, "name": "B", "extra": {"apiKey": "b", "baseUrl": "https://b.example/v1"}, "priority": 2})
    secret = client.post("/admin/api-keys", headers=admin, json={"name": "k", "allowedVirtualModels": []}).json()["secret"]
    respx.post("https://a.example/v1/chat/completions").mock(return_value=Response(429, json={"error": "rate"}))
    respx.post("https://b.example/v1/chat/completions").mock(
        return_value=Response(200, json={"choices": [{"message": {"content": "from-b"}}], "usage": {}})
    )
    r = client.post(
        "/v1/responses",
        headers={"Authorization": f"Bearer {secret}"},
        json={"model": "foo", "input": "hi"},
    )
    assert r.status_code == 200
    assert "from-b" in str(r.json())


def test_oauth_start_bridge_offline(client, admin):
    r = client.post(
        "/admin/oauth/start",
        headers=admin,
        json={"family": "gemini-cli", "baseUrl": "http://cliproxy-offline.test:8317"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "label" in body
    assert body.get("family") == "gemini-cli"
    assert body.get("ok") is False or body.get("bridgeOnline") is False or "EasyCLIProxy" in (body.get("message") or body.get("command") or "")
