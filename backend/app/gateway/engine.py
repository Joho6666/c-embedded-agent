from __future__ import annotations

import json
import random
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.ids import new_id
from app.core.limiter import add as window_add
from app.core.limiter import peek as window_peek
from app.core.limiter import remaining as rpm_remaining
from app.core.limiter import used as window_used
from app.core.security import decrypt_secret
from app.core.ssrf import validate_upstream_url
from app.core.state import get_state
from app.gateway.usage import normalize_usage, parse_sse_usage
from app.models.database import (
    CredentialRow,
    ModelPricingRow,
    ModelRow,
    ProviderRow,
    RequestLogRow,
    VirtualModelRow,
    utcnow,
)
from app.providers.base import AdapterContext, UpstreamError
from app.providers.registry import get_adapter

HARD_BLOCKED = {"disabled", "unauthorized", "circuit_open"}
QUOTA_DAILY = "quota_daily_exhausted"
QUOTA_MONTHLY = "quota_monthly_exhausted"
IMPLEMENTED_STRATEGIES = [
    "priority",
    "failover",
    "round_robin",
    "weighted_round_robin",
    "least_latency",
    "highest_success",
    "quota_aware",
    "health_aware",
    "random",
    "hybrid",
]


@dataclass
class RouteResult:
    payload: dict[str, Any] | None = None
    status_code: int = 200
    real_model: str = ""
    provider_id: str = ""
    credential_id: str = ""
    virtual_model: str = ""
    ttft_ms: int = 0
    latency_ms: int = 0
    retry_count: int = 0
    fallback_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    estimated_cost: float = 0.0
    error: str = ""
    error_code: str = ""
    error_type: str = "gateway_error"
    trace: list[dict[str, Any]] = field(default_factory=list)
    stream_iter: AsyncIterator[bytes] | None = None
    log_id: str = ""
    request_status: str = "pending"
    first_token_at: datetime | None = None
    client_disconnected: bool = False
    _t0: float = field(default_factory=time.perf_counter)


@dataclass
class ResolvedCandidate:
    credential: CredentialRow
    provider_id: str
    provider_name: str
    upstream_model: str
    priority: int
    weight: int
    latency: float
    success_rate: float
    quota_remaining: float
    rpm_remaining: int
    status: str
    score: float = 0.0
    reason: str = ""


def _today() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def _month() -> str:
    return datetime.utcnow().strftime("%Y-%m")


def _iso_now() -> str:
    return datetime.utcnow().strftime("%H:%M:%S.%f")[:-3]


def trace_event(
    result: RouteResult,
    message: str,
    *,
    type_: str = "info",
    provider: str = "",
    credential: str = "",
    model: str = "",
    extra: dict[str, Any] | None = None,
) -> None:
    elapsed = int((time.perf_counter() - result._t0) * 1000)
    kind = "info"
    if type_ in {"error", "circuit"}:
        kind = "error"
    elif type_ in {"warn", "retry", "failover", "quota"}:
        kind = "warn"
    elif type_ in {"ok", "selected", "completed"}:
        kind = "ok"
    event = {
        "at": _iso_now(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "durationMs": elapsed,
        "type": type_,
        "provider": provider,
        "credential": credential,
        "model": model,
        "message": message,
        "label": message,
        "kind": kind,
        "detail": "",
    }
    if extra:
        event.update(extra)
        if extra.get("detail"):
            event["detail"] = str(extra["detail"])
    result.trace.append(event)


def reset_daily_credential(row: CredentialRow) -> None:
    day = _today()
    if row.stats_day != day:
        row.stats_day = day
        row.requests_today = 0
        row.tokens_today = 0
        row.success_count = 0
        row.fail_count = 0
        if row.status == QUOTA_DAILY:
            row.status = "healthy"


def reset_monthly_credential(row: CredentialRow) -> None:
    month = _month()
    if getattr(row, "stats_month", "") != month:
        row.stats_month = month
        row.monthly_spend = 0
        if row.status == QUOTA_MONTHLY:
            row.status = "healthy"


def reset_daily_key(row: Any) -> None:
    day = _today()
    if getattr(row, "stats_day", "") != day:
        row.stats_day = day
        row.requests_today = 0
        row.tokens_today = 0


def reset_monthly_key(row: Any) -> None:
    month = _month()
    if getattr(row, "stats_month", "") != month:
        row.stats_month = month
        if hasattr(row, "monthly_spend"):
            row.monthly_spend = 0


def maybe_recover_circuit(row: CredentialRow) -> None:
    if row.status != "circuit_open" or not row.circuit_opened_at:
        return
    cooldown = get_settings().circuit_cooldown_s
    if datetime.utcnow() - row.circuit_opened_at >= timedelta(seconds=cooldown):
        row.status = "healthy"
        row.consecutive_failures = 0
        row.circuit_opened_at = None


def maybe_recover_rate_limit(row: CredentialRow) -> None:
    now = datetime.utcnow()
    if row.status in {"rate_limited", "cooling"}:
        if row.cooling_until and row.cooling_until <= now:
            row.status = "healthy"
            row.cooling_until = None


def extra_headers(extra: dict[str, Any]) -> dict[str, str]:
    raw = extra.get("headers") or extra.get("custom_headers") or ""
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    headers: dict[str, str] = {}
    if isinstance(raw, str) and raw.strip():
        for line in raw.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip()] = v.strip()
    return headers


def ctx_for(cred: CredentialRow, provider_type: str) -> AdapterContext:
    extra = json.loads(cred.extra_json or "{}")
    secret = decrypt_secret(cred.encrypted_secret) if cred.encrypted_secret else extra.get("apiKey", "")
    base = cred.base_url or extra.get("baseUrl") or extra.get("base_url") or ""
    validate_upstream_url(base, provider_type)
    return AdapterContext(
        base_url=base,
        api_key=secret,
        headers=extra_headers(extra),
        timeout_s=get_settings().request_timeout_s,
    )


def success_rate(row: CredentialRow) -> float:
    total = row.success_count + row.fail_count
    return (row.success_count / total) if total else 1.0


def quota_remaining(row: CredentialRow) -> float:
    reset_daily_credential(row)
    reset_monthly_credential(row)
    tok = 1 - (row.tokens_today / max(row.daily_token_limit, 1))
    req = 1 - (row.requests_today / max(row.daily_request_limit, 1))
    budget = 1.0
    if row.monthly_budget:
        budget = 1 - (row.monthly_spend / max(row.monthly_budget, 0.01))
    return min(max(tok, 0), 1) * 0.4 + min(max(req, 0), 1) * 0.3 + min(max(budget, 0), 1) * 0.3


def credential_static_quota_ok(row: CredentialRow) -> bool:
    reset_daily_credential(row)
    reset_monthly_credential(row)
    if row.daily_request_limit and row.requests_today >= row.daily_request_limit:
        row.status = QUOTA_DAILY
        return False
    if row.daily_token_limit and row.tokens_today >= row.daily_token_limit:
        row.status = QUOTA_DAILY
        return False
    if row.monthly_budget and row.monthly_spend >= row.monthly_budget:
        row.status = QUOTA_MONTHLY
        return False
    return True


def credential_quota_ok(row: CredentialRow) -> bool:
    """Eligibility only — never consumes RPM/TPM."""
    return credential_eligible(row)


def credential_eligible(row: CredentialRow) -> bool:
    if not row.enabled:
        return False
    maybe_recover_circuit(row)
    maybe_recover_rate_limit(row)
    reset_daily_credential(row)
    reset_monthly_credential(row)
    if row.status in HARD_BLOCKED:
        return False
    if row.status in {QUOTA_DAILY, QUOTA_MONTHLY}:
        if not credential_static_quota_ok(row):
            return False
        if row.status in {QUOTA_DAILY, QUOTA_MONTHLY}:
            return False
    if row.status in {"cooling", "rate_limited"} and row.cooling_until and row.cooling_until > datetime.utcnow():
        return False
    if not credential_static_quota_ok(row):
        return False
    if not window_peek(f"cred-rpm:{row.id}", row.rpm_limit):
        return False
    if not window_peek(f"cred-tpm:{row.id}", row.tpm_limit, amount=1):
        return False
    return True


def consume_credential_rpm(row: CredentialRow) -> bool:
    from app.core.limiter import allow as rpm_allow

    if not rpm_allow(f"cred-rpm:{row.id}", row.rpm_limit):
        row.status = "rate_limited"
        row.cooling_until = datetime.utcnow() + timedelta(seconds=30)
        return False
    return True


def consume_credential_quota(row: CredentialRow, estimated_tokens: int) -> str | None:
    from app.core.limiter import allow as rpm_allow

    from app.core.limiter import allow as tpm_allow

    if estimated_tokens > 0 and row.tpm_limit and not tpm_allow(f"cred-tpm:{row.id}", row.tpm_limit, amount=max(1, estimated_tokens)):
        row.status = "rate_limited"
        row.cooling_until = datetime.utcnow() + timedelta(seconds=30)
        return "tpm_exceeded"
    if not rpm_allow(f"cred-rpm:{row.id}", row.rpm_limit):
        row.status = "rate_limited"
        row.cooling_until = datetime.utcnow() + timedelta(seconds=30)
        return "rpm_exceeded"
    return None


def record_credential_tokens(row: CredentialRow, tokens: int, estimated: int = 0) -> None:
    extra = max(0, tokens - max(0, estimated))
    if extra:
        window_add(f"cred-tpm:{row.id}", extra)


def mark_success(row: CredentialRow, latency_ms: int, tokens: int, cost: float = 0) -> None:
    reset_daily_credential(row)
    reset_monthly_credential(row)
    row.status = "healthy"
    row.consecutive_failures = 0
    row.circuit_opened_at = None
    row.last_error = ""
    row.last_used_at = utcnow()
    row.requests_today += 1
    row.tokens_today += tokens
    row.monthly_spend += cost
    row.success_count += 1
    if row.avg_latency_ms:
        row.avg_latency_ms = (row.avg_latency_ms * 0.8) + (latency_ms * 0.2)
    else:
        row.avg_latency_ms = latency_ms


def mark_failure(row: CredentialRow, status: int, message: str) -> None:
    reset_daily_credential(row)
    row.last_error = message[:800]
    row.last_used_at = utcnow()
    row.fail_count += 1
    row.consecutive_failures += 1
    if status in (401, 403):
        row.status = "unauthorized"
        return
    if status == 429:
        row.status = "rate_limited"
        row.cooling_until = datetime.utcnow() + timedelta(seconds=30)
    if row.consecutive_failures >= get_settings().circuit_fail_threshold:
        row.status = "circuit_open"
        row.circuit_opened_at = utcnow()


def eligible_credentials(db: Session, provider_id: str | None = None) -> list[CredentialRow]:
    q = db.query(CredentialRow).filter(CredentialRow.enabled.is_(True))
    if provider_id:
        q = q.filter(CredentialRow.provider_id == provider_id)
    rows = q.all()
    return [row for row in rows if credential_eligible(row)]


def hybrid_score(row: CredentialRow) -> float:
    lat = 1 / (1 + (row.avg_latency_ms or 800) / 1000)
    return success_rate(row) * 0.4 + quota_remaining(row) * 0.3 + lat * 0.3


def order_credentials(rows: list[CredentialRow], strategy: str, scope: str) -> list[CredentialRow]:
    resolved = [
        ResolvedCandidate(
            credential=r,
            provider_id=r.provider_id,
            provider_name=r.name,
            upstream_model="",
            priority=r.priority,
            weight=r.weight,
            latency=r.avg_latency_ms or 10_000,
            success_rate=success_rate(r),
            quota_remaining=quota_remaining(r),
            rpm_remaining=rpm_remaining(f"cred-rpm:{r.id}", r.rpm_limit),
            status=r.status,
        )
        for r in rows
    ]
    ordered = apply_strategy(resolved, strategy, scope)
    return [c.credential for c in ordered]


def apply_strategy(cands: list[ResolvedCandidate], strategy: str, scope: str) -> list[ResolvedCandidate]:
    if not cands:
        return []
    if strategy in {"priority", "failover"}:
        out = sorted(cands, key=lambda c: (c.priority, -c.weight))
        for i, c in enumerate(out):
            c.score = float(len(out) - i)
            c.reason = f"priority={c.priority}"
        return out
    if strategy == "round_robin":
        ordered = sorted(cands, key=lambda c: (c.priority, c.credential.id))
        i = get_state().next_round_robin(f"rr:{scope}", len(ordered))
        rotated = ordered[i:] + ordered[:i]
        for idx, c in enumerate(rotated):
            c.score = float(len(rotated) - idx)
            c.reason = "round_robin"
        return rotated
    if strategy == "weighted_round_robin":
        items = [(c.credential.id, max(1, c.weight)) for c in cands]
        pick_id = get_state().smooth_wrr_pick(scope, items)
        picked = next((c for c in cands if c.credential.id == pick_id), cands[0])
        rest = [c for c in cands if c.credential.id != picked.credential.id]
        picked.score = 1.0
        picked.reason = f"smooth_wrr weight={picked.weight}"
        for c in rest:
            c.score = 0.0
            c.reason = f"smooth_wrr weight={c.weight}"
        return [picked] + rest
    if strategy == "least_latency":
        out = sorted(cands, key=lambda c: (c.latency, c.priority))
        for c in out:
            c.score = 1 / (1 + c.latency / 1000)
            c.reason = f"latency={int(c.latency)}ms"
        return out
    if strategy == "highest_success":
        out = sorted(cands, key=lambda c: (-c.success_rate, c.priority))
        for c in out:
            c.score = c.success_rate
            c.reason = f"success={c.success_rate:.2f}"
        return out
    if strategy == "quota_aware":
        out = sorted(cands, key=lambda c: (-c.quota_remaining, -c.rpm_remaining, c.priority))
        for c in out:
            c.score = c.quota_remaining
            c.reason = f"quota={c.quota_remaining:.2f} rpm_left={c.rpm_remaining}"
        return out
    if strategy == "random":
        shuffled = list(cands)
        random.shuffle(shuffled)
        for c in shuffled:
            c.score = 0.0
            c.reason = "random"
        return shuffled
    if strategy == "hybrid":
        for c in cands:
            c.score = hybrid_score(c.credential)
            c.reason = f"hybrid={c.score:.2f}"
        return sorted(cands, key=lambda c: -c.score)
    out = sorted(
        cands,
        key=lambda c: (0 if c.status == "healthy" else 1, -c.success_rate, c.latency, c.priority),
    )
    for c in out:
        c.score = c.success_rate
        c.reason = f"health status={c.status} success={c.success_rate:.2f}"
    return out


def resolve_virtual(db: Session, model: str) -> VirtualModelRow | None:
    return db.query(VirtualModelRow).filter(VirtualModelRow.slug == model).one_or_none()


def _to_resolved(db: Session, cred: CredentialRow, upstream_model: str, priority: int, weight: int) -> ResolvedCandidate:
    provider = db.get(ProviderRow, cred.provider_id)
    return ResolvedCandidate(
        credential=cred,
        provider_id=cred.provider_id,
        provider_name=provider.name if provider else cred.name,
        upstream_model=upstream_model,
        priority=priority,
        weight=weight,
        latency=cred.avg_latency_ms or 10_000,
        success_rate=success_rate(cred),
        quota_remaining=quota_remaining(cred),
        rpm_remaining=rpm_remaining(f"cred-rpm:{cred.id}", cred.rpm_limit),
        status=cred.status,
    )


def resolve_candidates(db: Session, requested: str) -> tuple[str, str, list[ResolvedCandidate]]:
    vm = resolve_virtual(db, requested)
    if vm:
        strategy = vm.strategy if vm.strategy in IMPLEMENTED_STRATEGIES else "failover"
        defs = json.loads(vm.candidates_json or "[]")
        resolved: list[ResolvedCandidate] = []
        seen: set[str] = set()
        for item in defs:
            cred_id = item.get("credentialId") or item.get("credential_id")
            model_id = item.get("modelId") or item.get("model_id") or item.get("upstream_model") or requested
            priority = int(item.get("priority") or 99)
            weight = int(item.get("weight") or 100)
            upstream = str(model_id)
            model_row = db.get(ModelRow, model_id) if model_id else None
            if model_row is None:
                model_row = db.query(ModelRow).filter(ModelRow.model_id == str(model_id)).first()
            if model_row:
                upstream = model_row.model_id
            if cred_id:
                cred = db.get(CredentialRow, cred_id)
                if cred and credential_eligible(cred):
                    key = f"{cred.id}:{upstream}"
                    if key not in seen:
                        seen.add(key)
                        resolved.append(_to_resolved(db, cred, upstream, priority, weight))
                continue
            provider_id = model_row.provider_id if model_row else None
            for cred in eligible_credentials(db, provider_id):
                key = f"{cred.id}:{upstream}"
                if key in seen:
                    continue
                seen.add(key)
                resolved.append(_to_resolved(db, cred, upstream, priority, weight or cred.weight))
        if not resolved:
            for cred in eligible_credentials(db):
                resolved.append(_to_resolved(db, cred, requested, cred.priority, cred.weight))
        return vm.slug, strategy, resolved

    model_row = db.query(ModelRow).filter(ModelRow.model_id == requested).first()
    provider_id = model_row.provider_id if model_row else None
    creds = eligible_credentials(db, provider_id)
    resolved = [_to_resolved(db, c, requested, c.priority, c.weight) for c in creds]
    return "", "failover", resolved


def candidate_queue(db: Session, requested: str) -> tuple[str, str, list[tuple[CredentialRow, str]]]:
    virtual, strategy, resolved = resolve_candidates(db, requested)
    ordered = apply_strategy(resolved, strategy, virtual or requested)
    return virtual, strategy, [(c.credential, c.upstream_model) for c in ordered]


def estimate_cost(db: Session, model: str, usage: dict[str, int]) -> float:
    row = (
        db.query(ModelPricingRow)
        .filter(ModelPricingRow.model == model)
        .order_by(ModelPricingRow.effective_from.desc())
        .first()
    )
    if not row:
        return 0.0
    inp = usage["input_tokens"] / 1_000_000 * row.input_per_1m
    out = usage["output_tokens"] / 1_000_000 * row.output_per_1m
    cached = usage["cached_tokens"] / 1_000_000 * row.cached_input_per_1m
    reasoning = usage.get("reasoning_tokens", 0) / 1_000_000 * getattr(row, "reasoning_per_1m", 0)
    return round(inp + out + cached + reasoning, 6)


def apply_usage(result: RouteResult, usage: dict[str, int]) -> None:
    result.input_tokens = usage["input_tokens"]
    result.output_tokens = usage["output_tokens"]
    result.cached_tokens = usage["cached_tokens"]
    result.reasoning_tokens = usage["reasoning_tokens"]


def persist_log(db: Session, result: RouteResult, key_id: str, requested: str, stream: bool) -> RequestLogRow:
    now = utcnow()
    row = None
    if result.log_id:
        row = db.get(RequestLogRow, result.log_id)
    if row is None:
        row = RequestLogRow(id=result.log_id or new_id("req"))
        db.add(row)
        result.log_id = row.id
    row.timestamp = row.timestamp or now
    row.request_status = result.request_status
    row.started_at = row.started_at or now
    row.first_token_at = result.first_token_at or row.first_token_at
    terminal = result.request_status in {"ok", "error", "cancelled"}
    row.completed_at = now if terminal else None
    row.stream_completed = stream and result.request_status == "ok"
    row.client_disconnected = result.client_disconnected
    if key_id:
        row.gateway_api_key_id = key_id
    row.requested_model = requested
    row.virtual_model = result.virtual_model
    row.real_model = result.real_model
    row.provider_id = result.provider_id
    row.credential_id = result.credential_id
    row.input_tokens = result.input_tokens
    row.output_tokens = result.output_tokens
    row.cached_tokens = result.cached_tokens
    row.reasoning_tokens = result.reasoning_tokens
    row.total_tokens = result.input_tokens + result.output_tokens
    row.ttft_ms = result.ttft_ms
    row.latency_ms = result.latency_ms
    row.http_status = result.status_code
    row.retry_count = result.retry_count
    row.fallback_count = result.fallback_count
    row.estimated_cost = result.estimated_cost or estimate_cost(
        db,
        result.real_model or requested,
        {
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "cached_tokens": result.cached_tokens,
            "reasoning_tokens": result.reasoning_tokens,
        },
    )
    result.estimated_cost = row.estimated_cost
    row.error_message = result.error
    row.stream = stream
    row.trace_json = json.dumps(result.trace, ensure_ascii=False)
    return row


def begin_log(db: Session, key_id: str, requested: str, stream: bool, virtual: str) -> RequestLogRow:
    row = RequestLogRow(
        id=new_id("req"),
        timestamp=utcnow(),
        request_status="pending",
        started_at=utcnow(),
        gateway_api_key_id=key_id,
        requested_model=requested,
        virtual_model=virtual,
        stream=stream,
    )
    db.add(row)
    db.flush()
    return row


def update_log_status(result: RouteResult, status: str) -> None:
    result.request_status = status
    if not result.log_id:
        return
    from app.core.database import SessionLocal

    s = SessionLocal()
    try:
        row = s.get(RequestLogRow, result.log_id)
        if row:
            row.request_status = status
            if status == "streaming" and result.first_token_at:
                row.first_token_at = result.first_token_at
            if status in {"ok", "error", "cancelled"}:
                row.completed_at = utcnow()
            row.trace_json = json.dumps(result.trace, ensure_ascii=False)
            s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


def estimate_request_tokens(body: dict[str, Any], fallback: int = 512) -> int:
    for key in ("max_tokens", "max_completion_tokens", "max_output_tokens"):
        val = body.get(key)
        if isinstance(val, int) and val > 0:
            return val
    return fallback


def _bind_selected(result: RouteResult, cand: ResolvedCandidate) -> None:
    result.real_model = cand.upstream_model
    result.provider_id = cand.provider_id
    result.credential_id = cand.credential.id


async def execute_chat(db: Session, body: dict[str, Any], stream: bool = False, *, native_responses: bool = False, log_id: str = "") -> RouteResult:
    settings = get_settings()
    requested = str(body.get("model") or "")
    result = RouteResult(virtual_model="", real_model=requested, request_status="pending", log_id=log_id)
    trace_event(result, "Request received", type_="received", model=requested, extra={"detail": requested})
    result.request_status = "routing"
    virtual, strategy, resolved = resolve_candidates(db, requested)
    result.virtual_model = virtual
    if virtual:
        trace_event(result, f'Virtual Model "{virtual}" resolved', type_="virtual", model=virtual)
    trace_event(result, f"strategy={strategy}", type_="strategy", extra={"detail": strategy})
    ordered = apply_strategy(resolved, strategy, virtual or requested)
    for cand in ordered:
        trace_event(
            result,
            f"{cand.provider_name} score={cand.score:.2f} ({cand.reason})",
            type_="candidate",
            provider=cand.provider_name,
            credential=cand.credential.id,
            model=cand.upstream_model,
            extra={"detail": cand.reason, "score": round(cand.score, 4)},
        )
    if not ordered:
        result.status_code = 404
        result.error = f"No healthy credential for model '{requested}'"
        result.error_code = "no_healthy_credential"
        result.request_status = "error"
        trace_event(result, result.error, type_="error")
        return result

    estimated = estimate_request_tokens(body)
    attempts = 0
    last_error = ""
    last_status = 500
    last_code = "upstream_error"
    quota_exhausted_all = True
    max_attempts = min(settings.max_failover_attempts, len(ordered))
    for cand in ordered[:max_attempts]:
        cred = cand.credential
        if not credential_eligible(cred):
            continue
        consume_err = consume_credential_quota(cred, estimated)
        if consume_err:
            quota_exhausted_all = True
            trace_event(
                result,
                f"{cred.name} {consume_err}, skip",
                type_="quota",
                credential=cred.id,
                provider=cand.provider_name,
            )
            continue
        quota_exhausted_all = False
        attempts += 1
        provider = db.get(ProviderRow, cred.provider_id)
        ptype = provider.type if provider else "openai_compatible"
        adapter = get_adapter(ptype)
        try:
            ctx = ctx_for(cred, ptype)
        except ValueError as exc:
            last_error = str(exc)
            last_status = 400
            trace_event(result, "invalid upstream", type_="error", extra={"detail": str(exc)})
            continue
        call_body = dict(body)
        call_body["model"] = cand.upstream_model
        _bind_selected(result, cand)
        trace_event(
            result,
            f"Selected {cred.name}",
            type_="selected",
            provider=cand.provider_name,
            credential=cred.id,
            model=cand.upstream_model,
            extra={"detail": f"{cand.provider_name} / {cand.upstream_model}"},
        )
        result.request_status = "connecting"
        trace_event(result, "Upstream connection", type_="upstream", provider=cand.provider_name, credential=cred.id)
        started = time.perf_counter()
        try:
            if stream:
                if native_responses and getattr(adapter, "supports_native_responses", False):
                    agen = adapter.stream_responses(ctx, call_body)
                else:
                    agen = adapter.stream_chat_completion(ctx, call_body)
                first_buf = b""
                agen_iter = agen.__aiter__()
                try:
                    first_buf = await agen_iter.__anext__()
                except StopAsyncIteration:
                    first_buf = b""
                except UpstreamError:
                    raise
                except httpx.TimeoutException:
                    raise

                async def _wrap(
                    _iter=agen_iter,
                    _first=first_buf,
                    _started=started,
                    _cred_id=cred.id,
                    _model=cand.upstream_model,
                ) -> AsyncIterator[bytes]:
                    from app.core.database import SessionLocal

                    first = True
                    usage_acc: dict[str, int] = {}
                    try:
                        if _first:
                            result.ttft_ms = int((time.perf_counter() - _started) * 1000)
                            result.first_token_at = utcnow()
                            first = False
                            result.request_status = "streaming"
                            trace_event(result, "First token", type_="first_token", model=_model)
                            yield _first
                        async for chunk in _iter:
                            if first:
                                result.ttft_ms = int((time.perf_counter() - _started) * 1000)
                                result.first_token_at = utcnow()
                                first = False
                                result.request_status = "streaming"
                                trace_event(result, "First token", type_="first_token", model=_model)
                            text = chunk.decode("utf-8", errors="ignore")
                            for line in text.splitlines():
                                if line.startswith("data:"):
                                    raw = line[5:].strip()
                                    if raw and raw != "[DONE]":
                                        try:
                                            obj = json.loads(raw)
                                            parsed = parse_sse_usage(obj)
                                            if parsed:
                                                usage_acc = parsed
                                        except Exception:
                                            pass
                            yield chunk
                        latency = int((time.perf_counter() - _started) * 1000)
                        result.latency_ms = latency
                        if usage_acc:
                            apply_usage(result, usage_acc)
                        result.request_status = "ok"
                        result.status_code = 200
                        s = SessionLocal()
                        try:
                            row = s.get(CredentialRow, _cred_id)
                            if row:
                                cost = estimate_cost(s, _model, {
                                    "input_tokens": result.input_tokens,
                                    "output_tokens": result.output_tokens,
                                    "cached_tokens": result.cached_tokens,
                                    "reasoning_tokens": result.reasoning_tokens,
                                })
                                result.estimated_cost = cost
                                mark_success(row, latency, result.input_tokens + result.output_tokens, cost)
                                record_credential_tokens(row, result.input_tokens + result.output_tokens, estimated)
                                s.commit()
                        finally:
                            s.close()
                        trace_event(result, "Response completed", type_="completed")
                        trace_event(
                            result,
                            f"Usage recorded in={result.input_tokens} out={result.output_tokens}",
                            type_="usage",
                        )
                        trace_event(result, f"Cost calculated {result.estimated_cost}", type_="cost")
                        s = SessionLocal()
                        try:
                            persist_log(s, result, "", requested, True)
                            s.commit()
                        finally:
                            s.close()
                    except (GeneratorExit, httpx.RequestError) as exc:
                        if isinstance(exc, GeneratorExit) or result.client_disconnected:
                            result.request_status = "cancelled"
                            result.client_disconnected = True
                            result.error = "client disconnected"
                            result.error_code = "cancelled"
                            raise
                        raise
                    except UpstreamError as exc:
                        result.status_code = exc.status_code
                        result.error = exc.message
                        result.request_status = "error"
                        s = SessionLocal()
                        try:
                            row = s.get(CredentialRow, _cred_id)
                            if row:
                                mark_failure(row, exc.status_code, exc.message)
                                s.commit()
                        finally:
                            s.close()
                        raise
                    except httpx.TimeoutException as exc:
                        result.status_code = 504
                        result.error = "timeout"
                        result.request_status = "error"
                        s = SessionLocal()
                        try:
                            row = s.get(CredentialRow, _cred_id)
                            if row:
                                mark_failure(row, 504, "timeout")
                                s.commit()
                        finally:
                            s.close()
                        raise UpstreamError(504, "timeout", True) from exc

                result.stream_iter = _wrap()
                result.retry_count = max(0, attempts - 1)
                result.fallback_count = max(0, attempts - 1)
                result.status_code = 200
                result.request_status = "connecting"
                return result

            if native_responses:
                if getattr(adapter, "supports_native_responses", False):
                    chat = await adapter.responses(ctx, call_body)
                    trace_event(result, "Native Responses", type_="upstream", provider=cand.provider_name)
                else:
                    from app.providers.transform import chat_body_from_responses, responses_from_chat
                    from app.providers.base import ChatResult as CR

                    chat_body = chat_body_from_responses(call_body)
                    chat_body["model"] = cand.upstream_model
                    raw = await adapter.chat_completion(ctx, chat_body)
                    chat = responses_from_chat(CR(status_code=200, payload=raw.payload))
                    trace_event(result, "Responses fallback via Chat Completions", type_="upstream")
            else:
                chat = await adapter.chat_completion(ctx, call_body)
            latency = int((time.perf_counter() - started) * 1000)
            usage = normalize_usage(chat.payload)
            apply_usage(result, usage)
            cost = estimate_cost(db, chat.payload.get("model") or cand.upstream_model, usage)
            result.estimated_cost = cost
            record_credential_tokens(cred, usage["total_tokens"], estimated)
            mark_success(cred, latency, usage["total_tokens"], cost)
            result.payload = chat.payload
            result.status_code = 200
            result.request_status = "ok"
            result.real_model = chat.payload.get("model") or cand.upstream_model
            result.latency_ms = latency
            result.ttft_ms = latency
            result.retry_count = max(0, attempts - 1)
            result.fallback_count = max(0, attempts - 1)
            trace_event(result, "200 OK", type_="ok")
            trace_event(result, "Response completed", type_="completed")
            trace_event(result, f"Usage recorded in={result.input_tokens} out={result.output_tokens}", type_="usage")
            trace_event(result, f"Cost calculated {cost}", type_="cost")
            return result
        except UpstreamError as exc:
            last_error = exc.message
            last_status = exc.status_code
            last_code = "upstream_error"
            mark_failure(cred, exc.status_code, exc.message)
            trace_event(result, str(exc.status_code), type_="error", extra={"detail": exc.message[:200]})
            if exc.status_code in (401, 403):
                trace_event(result, "Credential unauthorized, skip retries on this key", type_="warn")
                continue
            if not exc.retryable:
                break
            trace_event(result, "Failover", type_="failover")
            continue
        except httpx.TimeoutException:
            last_error = "timeout"
            last_status = 504
            last_code = "timeout"
            mark_failure(cred, 504, "timeout")
            trace_event(result, "timeout", type_="error")
            trace_event(result, "Failover", type_="failover")
            continue
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            last_status = 502
            mark_failure(cred, 502, str(exc))
            trace_event(result, "error", type_="error", extra={"detail": str(exc)[:200]})
            continue

    result.status_code = last_status if last_status else 502
    if quota_exhausted_all and attempts == 0:
        result.status_code = 429
        result.error = "all credentials quota exhausted"
        result.error_code = "all_credentials_quota_exhausted"
    else:
        result.error = last_error or "upstream failed"
        result.error_code = last_code if last_error else "no_healthy_credential"
        if not last_error:
            result.status_code = 404
            result.error_code = "no_healthy_credential"
    result.request_status = "error"
    result.retry_count = max(0, attempts - 1)
    result.fallback_count = max(0, attempts - 1)
    return result


async def execute_responses(db: Session, body: dict[str, Any], stream: bool = False, log_id: str = "") -> RouteResult:
    return await execute_chat(db, body, stream=stream, native_responses=True, log_id=log_id)
