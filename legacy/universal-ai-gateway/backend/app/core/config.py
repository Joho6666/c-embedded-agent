from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT / ".env"), extra="ignore")

    database_url: str = f"sqlite:///{(DATA_DIR / 'gateway.db').as_posix()}"
    gateway_secret_key: str = ""
    credential_encryption_key: str = ""
    admin_api_key: str = Field(default="", validation_alias=AliasChoices("GATEWAY_ADMIN_API_KEY", "ADMIN_API_KEY"))
    admin_username: str = ""
    admin_password_hash: str = ""
    gateway_public_url: str = "http://localhost:8000/v1"
    redis_url: str = ""
    request_timeout_s: float = 60.0
    max_failover_attempts: int = 3
    circuit_fail_threshold: int = 5
    circuit_cooldown_s: int = 60
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    allow_local_upstream: bool = False
    app_env: str = "development"
    require_admin_login: bool = False
    log_retention_days: int = 30


@lru_cache
def get_settings() -> Settings:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return Settings()
