import hashlib
import secrets
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

_fernet: Fernet | None = None


def _fernet_key() -> bytes:
    settings = get_settings()
    raw = (settings.credential_encryption_key or settings.gateway_secret_key).encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    import base64

    return base64.urlsafe_b64encode(digest)


def fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_fernet_key())
    return _fernet


def encrypt_secret(plain: str) -> str:
    if not plain:
        return ""
    return fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    if not token:
        return ""
    try:
        return fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("credential decrypt failed") from exc


def mask_secret(plain: str) -> str:
    if not plain:
        return ""
    if len(plain) <= 8:
        return "****"
    return f"{plain[:4]}****{plain[-4:]}"


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def generate_gateway_key() -> str:
    return "sk-gw-" + secrets.token_urlsafe(24)


def timing_safe_eq(a: str, b: str) -> bool:
    return secrets.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
