from __future__ import annotations

import json
from datetime import datetime

from app.core.security import decrypt_secret, mask_secret
from app.models.database import ApiKeyRow, CredentialRow, ModelRow, ProviderRow, RequestLogRow, VirtualModelRow


def iso(v: datetime | None) -> str | None:
    return v.isoformat() + "Z" if v else None


def provider_out(p: ProviderRow, cred_count: int, model_count: int, req: int, tok: int, latency: float, success: float) -> dict:
    caps = json.loads(p.capabilities or "[]")
    return {
        "id": p.id,
        "descriptorId": p.descriptor_id,
        "name": p.name,
        "family": p.family,
        "status": p.status,
        "color": p.color,
        "mark": p.mark,
        "local": p.type == "ollama",
        "custom": p.type in {"custom", "openai_compatible"},
        "baseUrl": p.base_url,
        "capabilities": caps,
        "endpoints": ["chat", "responses"],
        "authSchemes": ["api_key", "bearer", "custom_header", "local"],
        "credentialCount": cred_count,
        "modelCount": model_count,
        "requestsToday": req,
        "tokensToday": tok,
        "costToday": 0,
        "latencyMs": int(latency),
        "successRate": round(success, 2),
    }


def credential_out(c: CredentialRow) -> dict:
    extra = json.loads(c.extra_json or "{}")
    secret = ""
    try:
        secret = decrypt_secret(c.encrypted_secret)
    except Exception:  # noqa: BLE001
        secret = ""
    total = c.success_count + c.fail_count
    success = (c.success_count / total * 100) if total else 100
    return {
        "id": c.id,
        "providerId": c.provider_id,
        "name": c.name,
        "authType": c.auth_type,
        "status": c.status,
        "priority": c.priority,
        "weight": c.weight,
        "maskedKey": mask_secret(secret),
        "extra": {k: v for k, v in extra.items() if k.lower() not in {"apikey", "api_key", "secret"}},
        "requestsToday": c.requests_today,
        "tokensToday": c.tokens_today,
        "avgLatencyMs": int(c.avg_latency_ms),
        "successRate": round(success, 2),
        "lastUsed": iso(c.last_used_at),
        "lastError": c.last_error or None,
        "coolingUntil": iso(c.cooling_until),
        "quota": {
            "rpmLimit": c.rpm_limit,
            "rpmUsed": 0,
            "tpmLimit": c.tpm_limit,
            "tpmUsed": 0,
            "dailyRequestLimit": c.daily_request_limit,
            "dailyRequestUsed": c.requests_today,
            "dailyTokenLimit": c.daily_token_limit,
            "dailyTokenUsed": c.tokens_today,
            "monthlyBudget": c.monthly_budget,
            "monthlySpend": 0,
        },
        "errorHistory": [],
        "enabled": c.enabled,
    }


def model_out(m: ModelRow, cred_count: int) -> dict:
    return {
        "id": m.id,
        "providerId": m.provider_id,
        "name": m.name,
        "modelId": m.model_id,
        "capabilities": ["chat", "streaming"],
        "contextWindow": 0,
        "inputPrice": 0,
        "outputPrice": 0,
        "ttftMs": 0,
        "tokensPerSec": 0,
        "successRate": 100,
        "credentialCount": cred_count,
        "status": m.status,
        "tags": [],
    }


def virtual_out(v: VirtualModelRow) -> dict:
    return {
        "id": v.id,
        "slug": v.slug,
        "name": v.name,
        "description": v.description,
        "candidates": json.loads(v.candidates_json or "[]"),
        "strategy": v.strategy,
        "fallbackChain": json.loads(v.fallback_json or "[]"),
        "requestsToday": 0,
        "successRate": 100,
    }


def key_out(k: ApiKeyRow, secret: str | None = None) -> dict:
    return {
        "id": k.id,
        "name": k.name,
        "prefix": k.key_prefix,
        "secret": secret or f"{k.key_prefix}…",
        "status": "active" if k.enabled else "disabled",
        "allowedVirtualModels": json.loads(k.allowed_models or "[]"),
        "rpmLimit": k.rpm_limit,
        "tpmLimit": k.tpm_limit,
        "dailyTokenLimit": k.daily_token_limit,
        "monthlyBudget": k.monthly_budget,
        "ipWhitelist": [],
        "lastUsed": iso(k.last_used_at),
        "requestsToday": k.requests_today,
        "tokensToday": k.tokens_today,
        "costToday": 0,
    }


def log_out(r: RequestLogRow) -> dict:
    status: int | str = r.http_status
    if r.http_status == 504:
        status = "timeout"
    return {
        "id": r.id,
        "callId": r.id,
        "time": iso(r.timestamp),
        "clientKeyId": r.gateway_api_key_id,
        "virtualModel": r.virtual_model or r.requested_model,
        "realModel": r.real_model,
        "providerId": r.provider_id,
        "credentialId": r.credential_id,
        "status": status,
        "inputTokens": r.input_tokens,
        "outputTokens": r.output_tokens,
        "cachedTokens": 0,
        "ttftMs": r.ttft_ms,
        "latencyMs": r.latency_ms,
        "retries": r.retry_count,
        "fallbackCount": r.fallback_count,
        "cost": r.estimated_cost,
        "stream": r.stream,
        "error": r.error_message or None,
        "trace": json.loads(r.trace_json or "[]"),
    }
