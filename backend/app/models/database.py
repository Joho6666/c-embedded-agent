from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class ProviderRow(Base):
    __tablename__ = "providers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    type: Mapped[str] = mapped_column(String(40))  # openai_compatible | gemini | ollama | custom
    descriptor_id: Mapped[str] = mapped_column(String(64), default="custom-openai")
    status: Mapped[str] = mapped_column(String(32), default="operational")
    base_url: Mapped[str] = mapped_column(String(500), default="")
    capabilities: Mapped[str] = mapped_column(Text, default="[]")
    color: Mapped[str] = mapped_column(String(16), default="#94a3b8")
    mark: Mapped[str] = mapped_column(String(8), default="P")
    family: Mapped[str] = mapped_column(String(64), default="Custom")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CredentialRow(Base):
    __tablename__ = "credentials"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"), index=True)
    auth_type: Mapped[str] = mapped_column(String(32), default="api_key")
    base_url: Mapped[str] = mapped_column(String(500), default="")
    encrypted_secret: Mapped[str] = mapped_column(Text, default="")
    extra_json: Mapped[str] = mapped_column(Text, default="{}")
    priority: Mapped[int] = mapped_column(Integer, default=1)
    weight: Mapped[int] = mapped_column(Integer, default=100)
    status: Mapped[str] = mapped_column(String(32), default="healthy")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    rpm_limit: Mapped[int] = mapped_column(Integer, default=120)
    tpm_limit: Mapped[int] = mapped_column(Integer, default=400000)
    daily_token_limit: Mapped[int] = mapped_column(Integer, default=20000000)
    daily_request_limit: Mapped[int] = mapped_column(Integer, default=10000)
    monthly_budget: Mapped[float] = mapped_column(Float, default=20)
    requests_today: Mapped[int] = mapped_column(Integer, default=0)
    tokens_today: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    avg_latency_ms: Mapped[float] = mapped_column(Float, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default="")
    circuit_opened_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cooling_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    stats_day: Mapped[str] = mapped_column(String(10), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ModelRow(Base):
    __tablename__ = "models"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"), index=True)
    model_id: Mapped[str] = mapped_column(String(200), index=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(32), default="available")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class VirtualModelRow(Base):
    __tablename__ = "virtual_models"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    strategy: Mapped[str] = mapped_column(String(40), default="failover")
    candidates_json: Mapped[str] = mapped_column(Text, default="[]")
    fallback_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ApiKeyRow(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(16))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_models: Mapped[str] = mapped_column(Text, default="[]")
    rpm_limit: Mapped[int] = mapped_column(Integer, default=120)
    tpm_limit: Mapped[int] = mapped_column(Integer, default=400000)
    daily_token_limit: Mapped[int] = mapped_column(Integer, default=10000000)
    monthly_budget: Mapped[float] = mapped_column(Float, default=40)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    requests_today: Mapped[int] = mapped_column(Integer, default=0)
    tokens_today: Mapped[int] = mapped_column(Integer, default=0)
    stats_day: Mapped[str] = mapped_column(String(10), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RequestLogRow(Base):
    __tablename__ = "request_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    gateway_api_key_id: Mapped[str] = mapped_column(String(64), default="")
    requested_model: Mapped[str] = mapped_column(String(200), default="")
    virtual_model: Mapped[str] = mapped_column(String(80), default="")
    real_model: Mapped[str] = mapped_column(String(200), default="")
    provider_id: Mapped[str] = mapped_column(String(64), default="")
    credential_id: Mapped[str] = mapped_column(String(64), default="")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    ttft_ms: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    http_status: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    fallback_count: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    stream: Mapped[bool] = mapped_column(Boolean, default=False)
    trace_json: Mapped[str] = mapped_column(Text, default="[]")
