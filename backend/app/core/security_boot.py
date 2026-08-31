from __future__ import annotations

import logging
import sys

WEAK_DEFAULTS = {"", "dev-admin", "dev-secret", "dev-cred", "changeme", "admin", "password", "secret"}

logger = logging.getLogger("gateway.security")


def assert_production_secrets() -> None:
    from app.core.config import get_settings

    settings = get_settings()
    env = (settings.app_env or "development").lower()
    if env != "production":
        if not settings.admin_username:
            logger.warning("ADMIN_USERNAME is not set; admin panel has no login gate")
        return

    errors: list[str] = []
    admin_key = settings.admin_api_key or ""
    secret = settings.gateway_secret_key or ""
    cred_key = settings.credential_encryption_key or ""
    if len(admin_key) < 16 or admin_key.lower() in WEAK_DEFAULTS:
        errors.append("GATEWAY_ADMIN_API_KEY is missing, too short, or a default value")
    if len(secret) < 16 or secret.lower() in WEAK_DEFAULTS:
        errors.append("GATEWAY_SECRET_KEY is missing, too short, or a default value")
    if not cred_key or cred_key.lower() in WEAK_DEFAULTS:
        errors.append("CREDENTIAL_ENCRYPTION_KEY is empty or a default value")
    if settings.admin_password_hash and settings.admin_password_hash.lower() in WEAK_DEFAULTS:
        errors.append("ADMIN_PASSWORD_HASH looks like a default password")
    if not settings.admin_username:
        if settings.require_admin_login:
            errors.append("ADMIN_USERNAME is required when REQUIRE_ADMIN_LOGIN=true")
        else:
            logger.warning("production start without ADMIN_USERNAME; set REQUIRE_ADMIN_LOGIN=true to refuse")
    if errors:
        for item in errors:
            logger.error("production security: %s", item)
        print("Refusing to start in production with weak secrets:", file=sys.stderr)
        for item in errors:
            print(f"  - {item}", file=sys.stderr)
        raise SystemExit(2)
