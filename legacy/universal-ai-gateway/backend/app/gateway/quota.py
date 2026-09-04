from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.limiter import allow as rpm_allow
from app.core.limiter import peek as window_peek
from app.core.limiter import add as window_add
from app.core.limiter import used as window_used
from app.gateway.engine import estimate_request_tokens, reset_daily_key, reset_monthly_key
from app.models.database import ApiKeyRow


def quota_error(code: str, message: str, status: int = 429) -> dict[str, Any]:
    err_type = "invalid_request_error" if code == "model_not_allowed" else "rate_limit_error"
    return {
        "status": status,
        "body": {"error": {"message": message, "type": err_type, "code": code}},
    }


def check_key_quota(key: ApiKeyRow, body: dict[str, Any]) -> dict[str, Any] | None:
    reset_daily_key(key)
    reset_monthly_key(key)
    if not rpm_allow(f"key-rpm:{key.id}", key.rpm_limit):
        return quota_error("rpm_exceeded", "API key RPM limit exceeded")
    daily_req = getattr(key, "daily_request_limit", 0) or 0
    if daily_req and key.requests_today >= daily_req:
        return quota_error("daily_request_exceeded", "API key daily request limit exceeded")
    if key.daily_token_limit and key.tokens_today >= key.daily_token_limit:
        return quota_error("daily_token_exceeded", "API key daily token limit exceeded")
    if key.monthly_budget and getattr(key, "monthly_spend", 0) >= key.monthly_budget:
        return quota_error("monthly_budget_exceeded", "API key monthly budget exceeded")
    estimated = estimate_request_tokens(body)
    from app.core.limiter import allow as tpm_allow

    if key.tpm_limit and not tpm_allow(f"key-tpm:{key.id}", key.tpm_limit, amount=max(1, estimated)):
        return quota_error("tpm_exceeded", "API key TPM limit exceeded")
    return None


def record_key_usage(db: Session, key: ApiKeyRow, tokens: int, cost: float = 0, estimated: int = 0) -> None:
    reset_daily_key(key)
    reset_monthly_key(key)
    key.requests_today += 1
    key.tokens_today += tokens
    if hasattr(key, "monthly_spend"):
        key.monthly_spend += cost
    extra = max(0, tokens - max(0, estimated))
    if extra:
        window_add(f"key-tpm:{key.id}", extra)
    db.flush()


def key_window_used(key_id: str, kind: str) -> int:
    return window_used(f"key-{kind}:{key_id}")
