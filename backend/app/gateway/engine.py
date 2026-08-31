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
from app.core.limiter import allow as rpm_allow, remaining as rpm_remaining
from app.core.routing_state import next_index
from app.core.security import decrypt_secret
from app.core.ssrf import validate_upstream_url
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

BLOCKED_STATUSES = {"disabled", "unauthorized", "quota_exhausted", "circuit_open"}
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
    error: str = ""
    trace: list[dict[str, Any]] = field(default_factory=list)
    stream_iter: AsyncIterator[bytes] | None = None
    log_id: str = ""
    request_status: str = "pending"


def _today() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def reset_daily_credential(row: CredentialRow) -> None:
    day = _today()
    if row.stats_day != day:
        row.stats_day = day
        row.requests_today = 0
        row.tokens_today = 0
        row.success_count = 0
        row.fail_count = 0


def reset_daily_key(row: Any) -> None:
    day = _today()
    if getattr(row, "stats_day", "") != day:
        row.stats_day = day
        row.requests_today = 0
        row.tokens_today = 0


def maybe_recover_circuit(row: CredentialRow) -> None:
    if row.status != "circuit_open" or not row.circuit_opened_at:
        return
    cooldown = get_settings().circuit_cooldown_s
    if datetime.utcnow() - row.circuit_opened_at >= timedelta(seconds=cooldown):
        row.status = "healthy"
        row.consecutive_failures = 0
        row.circuit_opened_at = None


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
    tok = 1 - (row.tokens_today / max(row.daily_token_limit, 1))
    req = 1 - (row.requests_today / max(row.daily_request_limit, 1))
    return min(max(tok, 0), 1) * 0.6 + min(max(req, 0), 1) * 0.4


def credential_quota_ok(row: CredentialRow) -> bool:
    reset_daily_credential(row)
    if row.daily_request_limit and row.requests_today >= row.daily_request_limit:
        row.status = "quota_exhausted"
        return False
    if row.daily_token_limit and row.tokens_today >= row.daily_token_limit:
        row.status = "quota_exhausted"
        return False
    if row.monthly_budget and row.monthly_spend >= row.monthly_budget:
        row.status = "quota_exhausted"
        return False
    if not rpm_allow(f"cred-rpm:{row.id}", row.rpm_limit):
        row.status = "rate_limited"
        row.cooling_until = datetime.utcnow() + timedelta(seconds=30)
        return False
    return True


def mark_success(row: CredentialRow, latency_ms: int, tokens: int, cost: float = 0) -> None:
    reset_daily_credential(row)
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
    out = []
    now = datetime.utcnow()
    for row in rows:
        maybe_recover_circuit(row)
        reset_daily_credential(row)
        if row.status in BLOCKED_STATUSES:
            continue
        if row.status in {"cooling", "rate_limited"} and row.cooling_until and row.cooling_until > now:
            continue
        if not credential_quota_ok(row) and row.status == "quota_exhausted":
            continue
        if row.status == "rate_limited":
            continue
        out.append(row)
    return out


def order_credentials(rows: list[CredentialRow], strategy: str, scope: str) -> list[CredentialRow]:
    if not rows:
        return []
    if strategy in {"priority", "failover"}:
        return sorted(rows, key=lambda r: (r.priority, -r.weight))
    if strategy == "round_robin":
        i = next_index(f"rr:{scope}", len(rows))
        ordered = sorted(rows, key=lambda r: (r.priority, r.id))
        return ordered[i:] + ordered[:i]
    if strategy == "weighted_round_robin":
        pool = [r for r in rows for _ in range(max(1, r.weight // 10))]
        if not pool:
            pool = rows
        i = next_index(f"wrr:{scope}", len(pool))
        pick = pool[i]
        rest = [r for r in rows if r.id != pick.id]
        return [pick] + rest
    if strategy == "least_latency":
        return sorted(rows, key=lambda r: (r.avg_latency_ms or 10_000, r.priority))
    if strategy == "highest_success":
        return sorted(rows, key=lambda r: (-success_rate(r), r.priority))
    if strategy == "quota_aware":
        return sorted(rows, key=lambda r: (-quota_remaining(r), r.priority))
    if strategy == "random":
        shuffled = list(rows)
        random.shuffle(shuffled)
        return shuffled
    if strategy == "hybrid":
        def score(r: CredentialRow) -> float:
            lat = 1 / (1 + (r.avg_latency_ms or 800) / 1000)
            return success_rate(r) * 0.4 + quota_remaining(r) * 0.3 + lat * 0.3

        return sorted(rows, key=lambda r: -score(r))
    # health_aware
    return sorted(rows, key=lambda r: (0 if r.status == "healthy" else 1, -success_rate(r), r.avg_latency_ms or 10_000, r.priority))


def resolve_virtual(db: Session, model: str) -> VirtualModelRow | None:
    return db.query(VirtualModelRow).filter(VirtualModelRow.slug == model).one_or_none()


def candidate_queue(db: Session, requested: str) -> tuple[str, str, list[tuple[CredentialRow, str]]]:
    vm = resolve_virtual(db, requested)
    if vm:
        strategy = vm.strategy if vm.strategy in IMPLEMENTED_STRATEGIES else "failover"
        cands = json.loads(vm.candidates_json or "[]")
        queue: list[tuple[CredentialRow, str]] = []
        for item in sorted(cands, key=lambda x: (x.get("priority", 99), -x.get("weight", 0))):
            cred_id = item.get("credentialId") or item.get("credential_id")
            model_id = item.get("modelId") or item.get("model_id") or item.get("upstream_model") or requested
            cred = db.get(CredentialRow, cred_id) if cred_id else None
            if cred is None:
                model_row = db.query(ModelRow).filter(ModelRow.model_id == model_id).first()
                if model_row:
                    creds = eligible_credentials(db, model_row.provider_id)
                    ordered = order_credentials(creds, strategy, vm.slug)
                    cred = ordered[0] if ordered else None
                    model_id = model_row.model_id
            if cred and cred.enabled:
                maybe_recover_circuit(cred)
                if cred.status not in BLOCKED_STATUSES:
                    queue.append((cred, str(model_id)))
        if not queue:
            for cred in order_credentials(eligible_credentials(db), strategy, vm.slug):
                queue.append((cred, requested))
        return vm.slug, strategy, queue

    model_row = db.query(ModelRow).filter(ModelRow.model_id == requested).first()
    if model_row:
        creds = order_credentials(eligible_credentials(db, model_row.provider_id), "priority", requested)
        return "", "failover", [(c, requested) for c in creds]
    creds = order_credentials(eligible_credentials(db), "priority", requested)
    return "", "failover", [(c, requested) for c in creds]


def estimate_cost(db: Session, model: str, usage: dict[str, int]) -> float:
    row = db.query(ModelPricingRow).filter(ModelPricingRow.model == model).first()
    if not row:
        return 0.0
    inp = usage["input_tokens"] / 1_000_000 * row.input_per_1m
    out = usage["output_tokens"] / 1_000_000 * row.output_per_1m
    cached = usage["cached_tokens"] / 1_000_000 * row.cached_input_per_1m
    return round(inp + out + cached, 6)


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
    row.timestamp = now
    row.request_status = result.request_status
    row.started_at = row.started_at or now
    row.completed_at = now if result.request_status in {"ok", "error"} else None
    row.stream_completed = stream and result.request_status == "ok"
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
    row.estimated_cost = estimate_cost(db, result.real_model or requested, {
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "cached_tokens": result.cached_tokens,
    })
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


async def execute_chat(db: Session, body: dict[str, Any], stream: bool = False) -> RouteResult:
    settings = get_settings()
    requested = str(body.get("model") or "")
    virtual, strategy, queue = candidate_queue(db, requested)
    result = RouteResult(virtual_model=virtual, real_model=requested, request_status="pending")
    result.trace.append({"label": "Request received", "kind": "info", "detail": requested})
    if virtual:
        result.trace.append({"label": f"Selected virtual model: {virtual}", "kind": "info"})
    if not queue:
        result.status_code = 404
        result.error = f"No healthy credential for model '{requested}'"
        result.request_status = "error"
        result.trace.append({"label": result.error, "kind": "error"})
        return result

    attempts = 0
    last_error = ""
    last_status = 500
    max_attempts = min(settings.max_failover_attempts, len(queue))
    for cred, upstream_model in queue[:max_attempts]:
        attempts += 1
        provider = db.get(ProviderRow, cred.provider_id)
        ptype = provider.type if provider else "openai_compatible"
        adapter = get_adapter(ptype)
        try:
            ctx = ctx_for(cred, ptype)
        except ValueError as exc:
            last_error = str(exc)
            last_status = 400
            result.trace.append({"label": "invalid upstream", "kind": "error", "detail": str(exc)})
            continue
        call_body = dict(body)
        call_body["model"] = upstream_model
        result.trace.append(
            {
                "label": f"Selected {cred.name}",
                "kind": "info",
                "detail": f"{provider.name if provider else cred.provider_id} / {upstream_model}",
            }
        )
        started = time.perf_counter()
        try:
            if stream:
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

                async def _wrap(_iter=agen_iter, _first=first_buf, _started=started, _cred_id=cred.id) -> AsyncIterator[bytes]:
                    from app.core.database import SessionLocal

                    first = True
                    usage_acc: dict[str, int] = {}
                    try:
                        if _first:
                            result.ttft_ms = int((time.perf_counter() - _started) * 1000)
                            first = False
                            yield _first
                        async for chunk in _iter:
                            if first:
                                result.ttft_ms = int((time.perf_counter() - _started) * 1000)
                                first = False
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
                                mark_success(row, latency, result.input_tokens + result.output_tokens)
                                s.commit()
                        finally:
                            s.close()
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
                result.real_model = upstream_model
                result.provider_id = cred.provider_id
                result.credential_id = cred.id
                result.retry_count = max(0, attempts - 1)
                result.fallback_count = max(0, attempts - 1)
                result.status_code = 200
                result.request_status = "streaming"
                return result

            chat = await adapter.chat_completion(ctx, call_body)
            latency = int((time.perf_counter() - started) * 1000)
            usage = normalize_usage(chat.payload)
            apply_usage(result, usage)
            cost = estimate_cost(db, chat.payload.get("model") or upstream_model, usage)
            mark_success(cred, latency, usage["total_tokens"], cost)
            result.payload = chat.payload
            result.status_code = 200
            result.request_status = "ok"
            result.real_model = chat.payload.get("model") or upstream_model
            result.provider_id = cred.provider_id
            result.credential_id = cred.id
            result.latency_ms = latency
            result.ttft_ms = latency
            result.retry_count = max(0, attempts - 1)
            result.fallback_count = max(0, attempts - 1)
            result.trace.append({"label": "200 OK", "kind": "ok"})
            return result
        except UpstreamError as exc:
            last_error = exc.message
            last_status = exc.status_code
            mark_failure(cred, exc.status_code, exc.message)
            result.trace.append({"label": str(exc.status_code), "kind": "error", "detail": exc.message[:200]})
            if exc.status_code in (401, 403):
                result.trace.append({"label": "Credential unauthorized, skip retries on this key", "kind": "warn"})
                continue
            if not exc.retryable:
                break
            result.trace.append({"label": "Failover", "kind": "warn"})
            continue
        except httpx.TimeoutException:
            last_error = "timeout"
            last_status = 504
            mark_failure(cred, 504, "timeout")
            result.trace.append({"label": "timeout", "kind": "error"})
            result.trace.append({"label": "Failover", "kind": "warn"})
            continue
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            last_status = 502
            mark_failure(cred, 502, str(exc))
            result.trace.append({"label": "error", "kind": "error", "detail": str(exc)[:200]})
            continue

    result.status_code = last_status if last_status else 502
    result.error = last_error or "upstream failed"
    result.request_status = "error"
    result.retry_count = max(0, attempts - 1)
    result.fallback_count = max(0, attempts - 1)
    return result
