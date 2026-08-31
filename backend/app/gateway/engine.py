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
from app.core.security import decrypt_secret
from app.models.database import CredentialRow, ModelRow, ProviderRow, RequestLogRow, VirtualModelRow, utcnow
from app.providers.base import AdapterContext, UpstreamError
from app.providers.registry import get_adapter

BLOCKED_STATUSES = {"disabled", "unauthorized", "quota_exhausted", "circuit_open"}
RETRYABLE = {429, 500, 502, 503, 504}


@dataclass
class Attempt:
    credential_id: str
    provider_id: str
    model: str
    error: str = ""
    status: int = 0


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
    error: str = ""
    trace: list[dict[str, Any]] = field(default_factory=list)
    stream_iter: AsyncIterator[bytes] | None = None


def _today() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def _reset_daily(row: CredentialRow) -> None:
    day = _today()
    if row.stats_day != day:
        row.stats_day = day
        row.requests_today = 0
        row.tokens_today = 0
        row.success_count = 0
        row.fail_count = 0


def maybe_recover_circuit(row: CredentialRow) -> None:
    if row.status != "circuit_open" or not row.circuit_opened_at:
        return
    cooldown = get_settings().circuit_cooldown_s
    if datetime.utcnow() - row.circuit_opened_at >= timedelta(seconds=cooldown):
        row.status = "healthy"
        row.consecutive_failures = 0
        row.circuit_opened_at = None


def mark_success(row: CredentialRow, latency_ms: int, tokens: int) -> None:
    _reset_daily(row)
    row.status = "healthy"
    row.consecutive_failures = 0
    row.circuit_opened_at = None
    row.last_error = ""
    row.last_used_at = utcnow()
    row.requests_today += 1
    row.tokens_today += tokens
    row.success_count += 1
    if row.avg_latency_ms:
        row.avg_latency_ms = (row.avg_latency_ms * 0.8) + (latency_ms * 0.2)
    else:
        row.avg_latency_ms = latency_ms


def mark_failure(row: CredentialRow, status: int, message: str) -> None:
    _reset_daily(row)
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


def extra_headers(extra: dict[str, Any]) -> dict[str, str]:
    raw = extra.get("headers") or extra.get("custom_headers") or ""
    headers: dict[str, str] = {}
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    if isinstance(raw, str) and raw.strip():
        for line in raw.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip()] = v.strip()
    return headers


def ctx_for(cred: CredentialRow) -> AdapterContext:
    extra = json.loads(cred.extra_json or "{}")
    secret = decrypt_secret(cred.encrypted_secret) if cred.encrypted_secret else extra.get("apiKey", "")
    return AdapterContext(
        base_url=cred.base_url or extra.get("baseUrl") or extra.get("base_url") or "",
        api_key=secret,
        headers=extra_headers(extra),
        timeout_s=get_settings().request_timeout_s,
    )


def resolve_virtual(db: Session, model: str) -> VirtualModelRow | None:
    return db.query(VirtualModelRow).filter(VirtualModelRow.slug == model).one_or_none()


def eligible_credentials(db: Session, provider_id: str | None = None) -> list[CredentialRow]:
    q = db.query(CredentialRow).filter(CredentialRow.enabled.is_(True))
    if provider_id:
        q = q.filter(CredentialRow.provider_id == provider_id)
    rows = q.all()
    out = []
    now = datetime.utcnow()
    for row in rows:
        maybe_recover_circuit(row)
        if row.status in BLOCKED_STATUSES:
            continue
        if row.status == "cooling" and row.cooling_until and row.cooling_until > now:
            continue
        if row.status == "rate_limited" and row.cooling_until and row.cooling_until > now:
            continue
        out.append(row)
    return out


def order_credentials(rows: list[CredentialRow], strategy: str) -> list[CredentialRow]:
    if strategy == "weighted_round_robin":
        return sorted(rows, key=lambda r: random.random() / max(r.weight, 1), reverse=True)
    if strategy == "health_aware":
        return sorted(rows, key=lambda r: (0 if r.status == "healthy" else 1, r.priority, -r.weight))
    return sorted(rows, key=lambda r: (r.priority, -r.weight))


def candidate_queue(db: Session, requested: str) -> tuple[str, str, list[tuple[CredentialRow, str]]]:
    """Returns virtual_slug, strategy, list of (credential, upstream_model)."""
    vm = resolve_virtual(db, requested)
    if vm:
        cands = json.loads(vm.candidates_json or "[]")
        queue: list[tuple[CredentialRow, str]] = []
        for item in sorted(cands, key=lambda x: (x.get("priority", 99), -x.get("weight", 0))):
            cred_id = item.get("credentialId") or item.get("credential_id")
            model_id = item.get("modelId") or item.get("model_id") or item.get("upstream_model") or requested
            cred = None
            if cred_id:
                cred = db.get(CredentialRow, cred_id)
            if cred is None and model_id:
                model_row = db.query(ModelRow).filter(ModelRow.model_id == model_id).first()
                if model_row:
                    creds = eligible_credentials(db, model_row.provider_id)
                    cred = order_credentials(creds, vm.strategy)[0] if creds else None
                    model_id = model_row.model_id
            if cred and cred.enabled:
                maybe_recover_circuit(cred)
                if cred.status not in BLOCKED_STATUSES:
                    queue.append((cred, str(model_id)))
        if not queue:
            for cred in order_credentials(eligible_credentials(db), vm.strategy):
                queue.append((cred, requested))
        return vm.slug, vm.strategy, queue

    model_row = db.query(ModelRow).filter(ModelRow.model_id == requested).first()
    if model_row:
        creds = order_credentials(eligible_credentials(db, model_row.provider_id), "priority")
        return "", "failover", [(c, requested) for c in creds]

    creds = order_credentials(eligible_credentials(db), "priority")
    return "", "failover", [(c, requested) for c in creds]


def usage_of(payload: dict[str, Any]) -> tuple[int, int]:
    usage = payload.get("usage") or {}
    inp = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    out = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    return inp, out


async def execute_chat(db: Session, body: dict[str, Any], stream: bool = False) -> RouteResult:
    settings = get_settings()
    requested = str(body.get("model") or "")
    virtual, strategy, queue = candidate_queue(db, requested)
    result = RouteResult(virtual_model=virtual, real_model=requested)
    result.trace.append({"label": "Request received", "kind": "info", "detail": requested})
    if virtual:
        result.trace.append({"label": f"Selected virtual model: {virtual}", "kind": "info"})
    if not queue:
        result.status_code = 404
        result.error = f"No healthy credential for model '{requested}'"
        result.trace.append({"label": result.error, "kind": "error"})
        return result

    attempts = 0
    last_error = ""
    last_status = 500
    max_attempts = min(settings.max_failover_attempts, len(queue))
    for cred, upstream_model in queue[:max_attempts]:
        attempts += 1
        provider = db.get(ProviderRow, cred.provider_id)
        adapter = get_adapter(provider.type if provider else "openai_compatible")
        ctx = ctx_for(cred)
        if not ctx.base_url:
            last_error = "missing base_url"
            last_status = 400
            continue
        call_body = dict(body)
        call_body["model"] = upstream_model
        result.trace.append(
            {"label": f"Selected {cred.name}", "kind": "info", "detail": f"{provider.name if provider else cred.provider_id} / {upstream_model}"}
        )
        started = time.perf_counter()
        try:
            if stream:
                agen = adapter.stream_chat_completion(ctx, call_body)
                cred_id = cred.id

                async def _wrap(
                    _agen=agen,
                    _cred_id=cred_id,
                    _started=started,
                ) -> AsyncIterator[bytes]:
                    from app.core.database import SessionLocal

                    first = True
                    try:
                        async for chunk in _agen:
                            if first:
                                result.ttft_ms = int((time.perf_counter() - _started) * 1000)
                                first = False
                            yield chunk
                        latency = int((time.perf_counter() - _started) * 1000)
                        result.latency_ms = latency
                        s = SessionLocal()
                        try:
                            row = s.get(CredentialRow, _cred_id)
                            if row:
                                mark_success(row, latency, 0)
                                s.commit()
                        finally:
                            s.close()
                    except UpstreamError as exc:
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
                return result

            chat = await adapter.chat_completion(ctx, call_body)
            latency = int((time.perf_counter() - started) * 1000)
            inp, out = usage_of(chat.payload)
            mark_success(cred, latency, inp + out)
            result.payload = chat.payload
            result.status_code = 200
            result.real_model = chat.payload.get("model") or upstream_model
            result.provider_id = cred.provider_id
            result.credential_id = cred.id
            result.latency_ms = latency
            result.ttft_ms = latency
            result.input_tokens = inp
            result.output_tokens = out
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
    result.retry_count = max(0, attempts - 1)
    result.fallback_count = max(0, attempts - 1)
    return result


def persist_log(db: Session, result: RouteResult, key_id: str, requested: str, stream: bool) -> RequestLogRow:
    row = RequestLogRow(
        id=new_id("req"),
        timestamp=utcnow(),
        gateway_api_key_id=key_id,
        requested_model=requested,
        virtual_model=result.virtual_model,
        real_model=result.real_model,
        provider_id=result.provider_id,
        credential_id=result.credential_id,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        total_tokens=result.input_tokens + result.output_tokens,
        ttft_ms=result.ttft_ms,
        latency_ms=result.latency_ms,
        http_status=result.status_code,
        retry_count=result.retry_count,
        fallback_count=result.fallback_count,
        estimated_cost=0,
        error_message=result.error,
        stream=stream,
        trace_json=json.dumps(result.trace, ensure_ascii=False),
    )
    db.add(row)
    return row
