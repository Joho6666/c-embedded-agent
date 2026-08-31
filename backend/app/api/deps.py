from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import hash_api_key, timing_safe_eq
from app.models.database import ApiKeyRow, utcnow


def admin_auth(authorization: str | None = Header(default=None)) -> None:
    settings = get_settings()
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token or not timing_safe_eq(token, settings.admin_api_key):
        raise HTTPException(status_code=401, detail="invalid admin key")


def require_gateway_key(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> ApiKeyRow:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing api key")
    raw = authorization[7:].strip()
    row = db.query(ApiKeyRow).filter(ApiKeyRow.key_hash == hash_api_key(raw)).one_or_none()
    if not row or not row.enabled:
        raise HTTPException(status_code=401, detail="invalid api key")
    row.last_used_at = utcnow()
    return row
