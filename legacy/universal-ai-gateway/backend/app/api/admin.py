from __future__ import annotations

import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import admin_auth, get_db
from app.api.serializers import credential_out, key_out, log_out, model_out, pricing_out, provider_out, virtual_out
from app.core.ids import new_id
from app.core.security import encrypt_secret, generate_gateway_key, hash_api_key
from app.core.ssrf import validate_upstream_url
from app.core.state import state_status
from app.gateway.engine import ctx_for, maybe_recover_circuit
from app.models.database import (
    ApiKeyRow,
    CredentialRow,
    ModelPricingRow,
    ModelRow,
    ProviderRow,
    RequestLogRow,
    VirtualModelRow,
    utcnow,
)
from app.providers.registry import adapter_capabilities, get_adapter

router = APIRouter(prefix="/admin", dependencies=[Depends(admin_auth)])

DESCRIPTOR_DEFAULTS = {
    "openai": ("openai_compatible", "OpenAI", "OpenAI", "#10a37f", "OA", "https://api.openai.com/v1"),
    "openrouter": ("openai_compatible", "OpenRouter", "OpenRouter", "#6566f1", "OR", "https://openrouter.ai/api/v1"),
    "deepseek": ("openai_compatible", "DeepSeek", "DeepSeek", "#4d6bfe", "DS", "https://api.deepseek.com"),
    "glm": ("openai_compatible", "GLM", "Zhipu", "#165dff", "智", "https://open.bigmodel.cn/api/paas/v4"),
    "kimi": ("openai_compatible", "Kimi", "Moonshot", "#f5c518", "K", "https://api.moonshot.cn/v1"),
    "siliconflow": ("openai_compatible", "SiliconFlow", "SiliconFlow", "#7c5cfc", "SF", "https://api.siliconflow.cn/v1"),
    "volcengine": ("openai_compatible", "火山方舟", "ByteDance", "#1664ff", "火", "https://ark.cn-beijing.volces.com/api/v3"),
    "bailian": ("openai_compatible", "阿里云百炼", "Alibaba", "#ff6a00", "阿", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    "custom-openai": ("openai_compatible", "Custom OpenAI Compatible", "Custom", "#94a3b8", "CU", ""),
    "gemini": ("gemini", "Google Gemini", "Google", "#4285f4", "G", "https://generativelanguage.googleapis.com/v1beta"),
    "ollama": ("ollama", "Ollama", "Local", "#c2c2c2", "OL", "http://localhost:11434"),
    "cliproxy": ("external_bridge", "CLI OAuth Bridge", "CLIProxy", "#22d3ee", "CP", "http://127.0.0.1:8317"),
    "gemini-cli": ("external_bridge", "Gemini CLI OAuth", "Google", "#4285f4", "GC", "http://127.0.0.1:8317"),
    "claude-code": ("external_bridge", "Claude Code OAuth", "Anthropic", "#d97757", "CC", "http://127.0.0.1:8317"),
    "openai-codex": ("external_bridge", "OpenAI Codex OAuth", "OpenAI", "#10a37f", "CX", "http://127.0.0.1:8317"),
    "antigravity": ("external_bridge", "Antigravity OAuth", "Google", "#8ab4f8", "AG", "http://127.0.0.1:8317"),
}


class ProviderIn(BaseModel):
    descriptorId: str = "custom-openai"
    name: str | None = None
    baseUrl: str | None = None
    type: str | None = None


class CredentialIn(BaseModel):
    providerId: str
    name: str
    authType: str = "api_key"
    extra: dict = Field(default_factory=dict)
    priority: int = 1
    weight: int = 100
    baseUrl: str | None = None


class VirtualIn(BaseModel):
    slug: str
    name: str | None = None
    description: str = ""
    candidates: list[dict] = Field(default_factory=list)
    strategy: str = "failover"
    fallbackChain: list[str] = Field(default_factory=list)


class KeyIn(BaseModel):
    name: str
    allowedVirtualModels: list[str] = Field(default_factory=list)
    rpmLimit: int = 120
    tpmLimit: int = 400000
    dailyTokenLimit: int = 10000000
    dailyRequestLimit: int = 10000
    monthlyBudget: float = 40
    ipWhitelist: list[str] = Field(default_factory=list)


class PricingIn(BaseModel):
    provider: str = ""
    model: str
    inputPer1M: float = 0
    outputPer1M: float = 0
    cachedInputPer1M: float = 0
    reasoningPer1M: float = 0
    currency: str = "USD"
    effectiveFrom: str = ""


def _agg_provider(db: Session, pid: str) -> tuple[int, int, float, float]:
    creds = db.query(CredentialRow).filter(CredentialRow.provider_id == pid).all()
    req = sum(c.requests_today for c in creds)
    tok = sum(c.tokens_today for c in creds)
    lat = sum(c.avg_latency_ms for c in creds) / len(creds) if creds else 0
    ok = sum(c.success_count for c in creds)
    fail = sum(c.fail_count for c in creds)
    success = (ok / (ok + fail) * 100) if (ok + fail) else 100
    return req, tok, lat, success


@router.get("/providers")
def list_providers(db: Session = Depends(get_db)):
    rows = db.query(ProviderRow).all()
    out = []
    for p in rows:
        cc = db.query(CredentialRow).filter(CredentialRow.provider_id == p.id).count()
        mc = db.query(ModelRow).filter(ModelRow.provider_id == p.id).count()
        req, tok, lat, success = _agg_provider(db, p.id)
        out.append(provider_out(p, cc, mc, req, tok, lat, success))
    return out


@router.post("/providers")
def create_provider(body: ProviderIn, db: Session = Depends(get_db)):
    desc = body.descriptorId
    defaults = DESCRIPTOR_DEFAULTS.get(desc, DESCRIPTOR_DEFAULTS["custom-openai"])
    ptype, name, family, color, mark, base = defaults
    if body.type:
        ptype = body.type
    existing = db.get(ProviderRow, desc)
    if existing and desc != "custom-openai":
        cc = db.query(CredentialRow).filter(CredentialRow.provider_id == existing.id).count()
        mc = db.query(ModelRow).filter(ModelRow.provider_id == existing.id).count()
        req, tok, lat, success = _agg_provider(db, existing.id)
        return provider_out(existing, cc, mc, req, tok, lat, success)
    pid = desc if desc != "custom-openai" else new_id("prov")
    if db.get(ProviderRow, pid):
        pid = new_id("prov")
    base_url = body.baseUrl or base
    if base_url:
        try:
            validate_upstream_url(base_url, ptype)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    adapter = get_adapter(ptype)
    caps = adapter.capabilities().as_dict() if hasattr(adapter, "capabilities") else {}
    enabled_caps = [k for k, v in caps.items() if v]
    row = ProviderRow(
        id=pid,
        name=body.name or name,
        type=ptype,
        descriptor_id=desc,
        base_url=base_url,
        family=family,
        color=color,
        mark=mark,
        capabilities=json.dumps(enabled_caps or ["chat", "streaming", "responses"]),
    )
    db.add(row)
    db.flush()
    return provider_out(row, 0, 0, 0, 0, 0, 100)


@router.post("/providers/{pid}/test")
async def test_provider(pid: str, db: Session = Depends(get_db)):
    p = db.get(ProviderRow, pid)
    if not p:
        raise HTTPException(404, "provider not found")
    cred = (
        db.query(CredentialRow)
        .filter(CredentialRow.provider_id == pid, CredentialRow.enabled.is_(True))
        .order_by(CredentialRow.priority)
        .first()
    )
    if not cred:
        return {"ok": False, "latencyMs": 0, "message": "no credential"}
    adapter = get_adapter(p.type)
    ok, msg, code = await adapter.health_check(ctx_for(cred, p.type))
    return {"ok": ok, "latencyMs": 0, "message": msg, "status": code}


@router.post("/providers/{pid}/sync-models")
async def sync_models(pid: str, db: Session = Depends(get_db)):
    p = db.get(ProviderRow, pid)
    if not p:
        raise HTTPException(404, "provider not found")
    cred = (
        db.query(CredentialRow)
        .filter(CredentialRow.provider_id == pid, CredentialRow.enabled.is_(True))
        .order_by(CredentialRow.priority)
        .first()
    )
    if not cred:
        raise HTTPException(400, "no credential")
    adapter = get_adapter(p.type)
    ids = await adapter.list_models(ctx_for(cred, p.type))
    existing = {m.model_id: m for m in db.query(ModelRow).filter(ModelRow.provider_id == pid).all()}
    for mid in ids:
        if mid in existing:
            continue
        db.add(ModelRow(id=new_id("m"), provider_id=pid, model_id=mid, name=mid))
    db.flush()
    return {"synced": len(ids)}


@router.get("/credentials")
def list_credentials(db: Session = Depends(get_db)):
    return [credential_out(c) for c in db.query(CredentialRow).order_by(CredentialRow.created_at.desc()).all()]


@router.post("/credentials")
def create_credential(body: CredentialIn, db: Session = Depends(get_db)):
    p = db.get(ProviderRow, body.providerId)
    if not p:
        raise HTTPException(404, "provider not found")
    extra = dict(body.extra or {})
    secret = extra.pop("apiKey", None) or extra.pop("api_key", None) or extra.pop("secret", None) or ""
    base = body.baseUrl or extra.get("baseUrl") or extra.get("base_url") or p.base_url
    row = CredentialRow(
        id=new_id("cred"),
        name=body.name,
        provider_id=body.providerId,
        auth_type=body.authType,
        base_url=base or "",
        encrypted_secret=encrypt_secret(str(secret)),
        extra_json=json.dumps(extra, ensure_ascii=False),
        priority=body.priority,
        weight=body.weight,
        status="healthy",
    )
    db.add(row)
    db.flush()
    return credential_out(row)


@router.patch("/credentials/{cid}")
def patch_credential(cid: str, body: dict, db: Session = Depends(get_db)):
    row = db.get(CredentialRow, cid)
    if not row:
        raise HTTPException(404, "not found")
    if "enabled" in body:
        row.enabled = bool(body["enabled"])
        if row.enabled and row.status == "disabled":
            row.status = "healthy"
        if not row.enabled:
            row.status = "disabled"
    if "weight" in body:
        row.weight = int(body["weight"])
    if "priority" in body:
        row.priority = int(body["priority"])
    if "status" in body:
        row.status = str(body["status"])
    quota = body.get("quota")
    if isinstance(quota, dict):
        if "rpmLimit" in quota:
            row.rpm_limit = int(quota["rpmLimit"])
        if "monthlyBudget" in quota:
            row.monthly_budget = float(quota["monthlyBudget"])
    db.flush()
    return credential_out(row)


@router.post("/credentials/{cid}/test")
async def test_credential(cid: str, db: Session = Depends(get_db)):
    row = db.get(CredentialRow, cid)
    if not row:
        raise HTTPException(404, "not found")
    p = db.get(ProviderRow, row.provider_id)
    adapter = get_adapter(p.type if p else "openai_compatible")
    ok, msg, code = await adapter.health_check(ctx_for(row, p.type if p else "openai_compatible"))
    if ok:
        row.status = "healthy"
        row.last_error = ""
    else:
        row.last_error = msg
        if code in (401, 403):
            row.status = "unauthorized"
        elif code:
            row.status = "error"
    db.flush()
    return {"ok": ok, "message": msg}


class OAuthStartIn(BaseModel):
    family: str = "gemini-cli"
    baseUrl: str | None = None
    managementKey: str | None = None
    credentialId: str | None = None


@router.post("/oauth/start")
async def oauth_start(body: OAuthStartIn, db: Session = Depends(get_db)):
    from app.providers.external_bridge import start_official_oauth

    base = body.baseUrl or "http://127.0.0.1:8317"
    mgmt = body.managementKey or ""
    if body.credentialId:
        row = db.get(CredentialRow, body.credentialId)
        if not row:
            raise HTTPException(404, "credential not found")
        extra = json.loads(row.extra_json or "{}")
        base = row.base_url or extra.get("baseUrl") or base
        from app.core.security import decrypt_secret

        mgmt = mgmt or decrypt_secret(row.encrypted_secret)
    return await start_official_oauth(base, mgmt, body.family)


@router.post("/credentials/{cid}/recover")
def recover_credential(cid: str, db: Session = Depends(get_db)):
    row = db.get(CredentialRow, cid)
    if not row:
        raise HTTPException(404, "not found")
    row.status = "healthy"
    row.consecutive_failures = 0
    row.circuit_opened_at = None
    row.last_error = ""
    row.enabled = True
    db.flush()
    return credential_out(row)


@router.get("/models")
def list_models(db: Session = Depends(get_db)):
    rows = db.query(ModelRow).all()
    out = []
    for m in rows:
        cc = db.query(CredentialRow).filter(CredentialRow.provider_id == m.provider_id, CredentialRow.enabled.is_(True)).count()
        out.append(model_out(m, cc))
    return out


@router.get("/virtual-models")
def list_virtual(db: Session = Depends(get_db)):
    return [virtual_out(v) for v in db.query(VirtualModelRow).all()]


@router.post("/virtual-models")
def create_virtual(body: VirtualIn, db: Session = Depends(get_db)):
    if db.query(VirtualModelRow).filter(VirtualModelRow.slug == body.slug).one_or_none():
        raise HTTPException(400, "slug exists")
    row = VirtualModelRow(
        id=new_id("vm"),
        slug=body.slug,
        name=body.name or body.slug,
        description=body.description,
        strategy=body.strategy,
        candidates_json=json.dumps(body.candidates, ensure_ascii=False),
        fallback_json=json.dumps(body.fallbackChain, ensure_ascii=False),
    )
    db.add(row)
    db.flush()
    return virtual_out(row)


@router.patch("/virtual-models/{vid}")
def patch_virtual(vid: str, body: dict, db: Session = Depends(get_db)):
    row = db.get(VirtualModelRow, vid)
    if not row:
        raise HTTPException(404, "not found")
    if "candidates" in body:
        row.candidates_json = json.dumps(body["candidates"], ensure_ascii=False)
    if "strategy" in body:
        row.strategy = body["strategy"]
    if "fallbackChain" in body:
        row.fallback_json = json.dumps(body["fallbackChain"], ensure_ascii=False)
    db.flush()
    return virtual_out(row)


@router.get("/api-keys")
def list_keys(db: Session = Depends(get_db)):
    return [key_out(k) for k in db.query(ApiKeyRow).order_by(ApiKeyRow.created_at.desc()).all()]


@router.post("/api-keys")
def create_key(body: KeyIn, db: Session = Depends(get_db)):
    secret = generate_gateway_key()
    row = ApiKeyRow(
        id=new_id("key"),
        name=body.name,
        key_hash=hash_api_key(secret),
        key_prefix=secret[:10],
        enabled=True,
        allowed_models=json.dumps(body.allowedVirtualModels, ensure_ascii=False),
        rpm_limit=body.rpmLimit,
        tpm_limit=body.tpmLimit,
        daily_token_limit=body.dailyTokenLimit,
        daily_request_limit=body.dailyRequestLimit,
        monthly_budget=body.monthlyBudget,
    )
    db.add(row)
    db.flush()
    return key_out(row, secret=secret)


@router.post("/api-keys/{kid}/rotate")
def rotate_key(kid: str, db: Session = Depends(get_db)):
    row = db.get(ApiKeyRow, kid)
    if not row:
        raise HTTPException(404, "not found")
    secret = generate_gateway_key()
    row.key_hash = hash_api_key(secret)
    row.key_prefix = secret[:10]
    db.flush()
    return key_out(row, secret=secret)


@router.post("/api-keys/{kid}/toggle")
def toggle_key(kid: str, db: Session = Depends(get_db)):
    row = db.get(ApiKeyRow, kid)
    if not row:
        raise HTTPException(404, "not found")
    row.enabled = not row.enabled
    db.flush()
    return key_out(row)


@router.delete("/api-keys/{kid}")
def delete_key(kid: str, db: Session = Depends(get_db)):
    row = db.get(ApiKeyRow, kid)
    if not row:
        raise HTTPException(404, "not found")
    db.delete(row)
    return {"ok": True}


@router.get("/requests")
def list_requests(limit: int = 200, db: Session = Depends(get_db)):
    rows = db.query(RequestLogRow).order_by(RequestLogRow.timestamp.desc()).limit(limit).all()
    return [log_out(r) for r in rows]


@router.get("/usage")
def usage(db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(hours=24)
    rows = db.query(RequestLogRow).filter(RequestLogRow.timestamp >= since).all()
    total = len(rows)
    ok = sum(1 for r in rows if r.http_status == 200)
    tokens = sum(r.total_tokens for r in rows)
    latency = sum(r.latency_ms for r in rows) / total if total else 0
    ttft = sum(r.ttft_ms for r in rows) / total if total else 0
    return {
        "requestsToday": total,
        "tokensToday": tokens,
        "estimatedCost": round(sum(r.estimated_cost for r in rows), 6),
        "successRate": round((ok / total * 100) if total else 100, 2),
        "avgTtftMs": int(ttft),
        "avgLatencyMs": int(latency),
        "activeProviders": db.query(ProviderRow).count(),
        "healthyCredentials": db.query(CredentialRow).filter(CredentialRow.status == "healthy").count(),
        "circuitOpen": db.query(CredentialRow).filter(CredentialRow.status == "circuit_open").count(),
        "availableModels": db.query(ModelRow).count(),
        "rpm": 0,
        "activeClients": db.query(ApiKeyRow).filter(ApiKeyRow.enabled.is_(True)).count(),
    }


@router.get("/usage/trend")
def usage_trend(range: str = "today", db: Session = Depends(get_db)):
    hours = {"today": 24, "24h": 24, "7d": 24 * 7, "30d": 24 * 30}.get(range, 24)
    since = datetime.utcnow() - timedelta(hours=hours)
    rows = db.query(RequestLogRow).filter(RequestLogRow.timestamp >= since).all()
    buckets: dict[str, dict[str, float]] = {}
    for r in rows:
        key = r.timestamp.strftime("%m-%d %H:00") if hours <= 24 else r.timestamp.strftime("%m-%d")
        b = buckets.setdefault(key, {"requests": 0, "tokens": 0, "cost": 0, "errors": 0})
        b["requests"] += 1
        b["tokens"] += r.total_tokens
        b["cost"] += r.estimated_cost
        if r.http_status != 200:
            b["errors"] += 1
    trend = [{"t": k, **v} for k, v in sorted(buckets.items())]
    return {"range": range, "trend": trend}


@router.get("/capabilities")
def capabilities():
    from app.gateway.engine import IMPLEMENTED_STRATEGIES

    return {"strategies": IMPLEMENTED_STRATEGIES, "adapters": adapter_capabilities()}


@router.get("/providers/{pid}/capabilities")
def provider_capabilities(pid: str, db: Session = Depends(get_db)):
    p = db.get(ProviderRow, pid)
    if not p:
        raise HTTPException(404, "provider not found")
    adapter = get_adapter(p.type)
    return {"id": pid, "type": p.type, "capabilities": adapter.capabilities().as_dict()}


def _range_since(range: str, custom_from: str | None = None, custom_to: str | None = None):
    if range == "custom" and custom_from:
        start = datetime.fromisoformat(custom_from.replace("Z", ""))
        end = datetime.fromisoformat(custom_to.replace("Z", "")) if custom_to else datetime.utcnow()
        return start, end
    hours = {"today": 24, "24h": 24, "7d": 24 * 7, "30d": 24 * 30}.get(range, 24)
    return datetime.utcnow() - timedelta(hours=hours), datetime.utcnow()


def _usage_rows(db: Session, range: str, custom_from: str | None = None, custom_to: str | None = None):
    start, end = _range_since(range, custom_from, custom_to)
    return db.query(RequestLogRow).filter(RequestLogRow.timestamp >= start, RequestLogRow.timestamp <= end).all()


def _usage_metrics(rows: list[RequestLogRow]) -> dict:
    total = len(rows)
    ok = sum(1 for r in rows if r.http_status == 200)
    errors_429 = sum(1 for r in rows if r.http_status == 429)
    errors_5xx = sum(1 for r in rows if r.http_status >= 500)
    timeouts = sum(1 for r in rows if r.http_status == 504)
    fallbacks = sum(1 for r in rows if r.fallback_count)
    return {
        "requests": total,
        "inputTokens": sum(r.input_tokens for r in rows),
        "outputTokens": sum(r.output_tokens for r in rows),
        "cachedTokens": sum(r.cached_tokens for r in rows),
        "reasoningTokens": sum(r.reasoning_tokens for r in rows),
        "tokens": sum(r.total_tokens for r in rows),
        "cost": round(sum(r.estimated_cost for r in rows), 6),
        "successRate": round((ok / total * 100) if total else 100, 2),
        "ttft": int(sum(r.ttft_ms for r in rows) / total) if total else 0,
        "latency": int(sum(r.latency_ms for r in rows) / total) if total else 0,
        "count429": errors_429,
        "count5xx": errors_5xx,
        "timeout": timeouts,
        "fallbackRate": round((fallbacks / total * 100) if total else 0, 2),
    }


@router.get("/health")
def admin_health(db: Session = Depends(get_db)):
    creds = db.query(CredentialRow).all()
    for c in creds:
        maybe_recover_circuit(c)
    counts: dict[str, int] = {}
    for c in creds:
        counts[c.status] = counts.get(c.status, 0) + 1
    providers = []
    for p in db.query(ProviderRow).all():
        pc = [c for c in creds if c.provider_id == p.id]
        healthy = all(c.status in {"healthy", "rate_limited", "cooling"} for c in pc) if pc else True
        providers.append(
            {
                "providerId": p.id,
                "status": "operational" if healthy else "degraded",
                "latencyMs": int(sum(c.avg_latency_ms for c in pc) / len(pc)) if pc else 0,
                "successRate": 100,
            }
        )
    st = state_status()
    redis_status = st.get("redis") or "disabled"
    redis_comp = "operational" if redis_status == "connected" else ("down" if redis_status == "error" else "degraded")
    if redis_status == "disabled":
        redis_comp = "degraded"
    overall = "operational" if counts.get("circuit_open", 0) == 0 and redis_status != "error" else "degraded"
    db_kind = "SQLite"
    from app.core.config import get_settings

    if "postgres" in get_settings().database_url:
        db_kind = "PostgreSQL"
    return {
        "overall": overall,
        "checkedAt": utcnow().isoformat() + "Z",
        "stateBackend": st.get("mode"),
        "redis": redis_status,
        "components": [
            {"id": "gateway", "name": "Gateway", "status": "operational", "detail": "FastAPI"},
            {"id": "database", "name": "Database", "status": "operational", "detail": db_kind},
            {
                "id": "redis",
                "name": "Redis",
                "status": redis_comp if redis_status != "disabled" else "degraded",
                "detail": f"{redis_status}" + (f" · {st.get('error')}" if st.get("error") else ""),
            },
            {
                "id": "state",
                "name": "State Backend",
                "status": "operational" if st.get("mode") == "redis" else "degraded",
                "detail": st.get("mode", "memory"),
            },
            {"id": "providers", "name": "Providers", "status": overall, "detail": f"{len(providers)} providers"},
            {"id": "credentials", "name": "Credentials", "status": overall, "detail": f"{len(creds)} credentials"},
        ],
        "providers": providers,
        "credentialCounts": [{"status": k, "count": v} for k, v in counts.items()],
    }


@router.get("/circuit-breakers")
def circuits(db: Session = Depends(get_db)):
    rows = db.query(CredentialRow).filter(CredentialRow.status == "circuit_open").all()
    out = []
    for c in rows:
        remaining = 0
        if c.circuit_opened_at:
            end = c.circuit_opened_at + timedelta(seconds=60)
            remaining = max(0, int((end - datetime.utcnow()).total_seconds()))
        out.append(
            {
                "id": f"cb_{c.id}",
                "credentialId": c.id,
                "providerId": c.provider_id,
                "reason": "连续失败",
                "lastError": c.last_error,
                "failureCount": c.consecutive_failures,
                "openedAt": c.circuit_opened_at.isoformat() + "Z" if c.circuit_opened_at else None,
                "recoverAt": None,
                "cooldownRemainingSec": remaining,
            }
        )
    return out


@router.get("/model-pricing")
def list_pricing(db: Session = Depends(get_db)):
    return [pricing_out(r) for r in db.query(ModelPricingRow).all()]


@router.post("/model-pricing")
def create_pricing(body: PricingIn, db: Session = Depends(get_db)):
    row = ModelPricingRow(
        id=new_id("price"),
        provider=body.provider,
        model=body.model,
        input_per_1m=body.inputPer1M,
        output_per_1m=body.outputPer1M,
        cached_input_per_1m=body.cachedInputPer1M,
        reasoning_per_1m=body.reasoningPer1M,
        currency=body.currency,
        effective_from=body.effectiveFrom,
    )
    db.add(row)
    db.flush()
    return pricing_out(row)


@router.patch("/model-pricing/{pid}")
def patch_pricing(pid: str, body: dict, db: Session = Depends(get_db)):
    row = db.get(ModelPricingRow, pid)
    if not row:
        raise HTTPException(404, "not found")
    mapping = {
        "provider": "provider",
        "model": "model",
        "inputPer1M": "input_per_1m",
        "outputPer1M": "output_per_1m",
        "cachedInputPer1M": "cached_input_per_1m",
        "reasoningPer1M": "reasoning_per_1m",
        "currency": "currency",
        "effectiveFrom": "effective_from",
    }
    for src, dest in mapping.items():
        if src in body:
            setattr(row, dest, body[src])
    db.flush()
    return pricing_out(row)


@router.delete("/model-pricing/{pid}")
def delete_pricing(pid: str, db: Session = Depends(get_db)):
    row = db.get(ModelPricingRow, pid)
    if not row:
        raise HTTPException(404, "not found")
    db.delete(row)
    return {"ok": True}


@router.get("/usage/providers")
def usage_providers(range: str = "today", custom_from: str | None = None, custom_to: str | None = None, db: Session = Depends(get_db)):
    rows = _usage_rows(db, range, custom_from, custom_to)
    grouped: dict[str, list[RequestLogRow]] = {}
    for r in rows:
        grouped.setdefault(r.provider_id or "unknown", []).append(r)
    names = {p.id: p.name for p in db.query(ProviderRow).all()}
    return [{"id": k, "name": names.get(k, k), **_usage_metrics(v)} for k, v in grouped.items()]


@router.get("/usage/models")
def usage_models(range: str = "today", custom_from: str | None = None, custom_to: str | None = None, db: Session = Depends(get_db)):
    rows = _usage_rows(db, range, custom_from, custom_to)
    grouped: dict[str, list[RequestLogRow]] = {}
    for r in rows:
        grouped.setdefault(r.real_model or r.requested_model or "unknown", []).append(r)
    return [{"id": k, "name": k, **_usage_metrics(v)} for k, v in grouped.items()]


@router.get("/usage/credentials")
def usage_credentials(range: str = "today", custom_from: str | None = None, custom_to: str | None = None, db: Session = Depends(get_db)):
    rows = _usage_rows(db, range, custom_from, custom_to)
    grouped: dict[str, list[RequestLogRow]] = {}
    for r in rows:
        grouped.setdefault(r.credential_id or "unknown", []).append(r)
    names = {c.id: c.name for c in db.query(CredentialRow).all()}
    return [{"id": k, "name": names.get(k, k), **_usage_metrics(v)} for k, v in grouped.items()]


@router.get("/usage/api-keys")
def usage_api_keys(range: str = "today", custom_from: str | None = None, custom_to: str | None = None, db: Session = Depends(get_db)):
    rows = _usage_rows(db, range, custom_from, custom_to)
    grouped: dict[str, list[RequestLogRow]] = {}
    for r in rows:
        grouped.setdefault(r.gateway_api_key_id or "unknown", []).append(r)
    names = {k.id: k.name for k in db.query(ApiKeyRow).all()}
    return [{"id": k, "name": names.get(k, k), **_usage_metrics(v)} for k, v in grouped.items()]


@router.get("/usage/errors")
def usage_errors(range: str = "today", custom_from: str | None = None, custom_to: str | None = None, db: Session = Depends(get_db)):
    rows = _usage_rows(db, range, custom_from, custom_to)
    buckets = {"429": 0, "5xx": 0, "timeout": 0, "cancelled": 0, "other": 0}
    for r in rows:
        if r.request_status == "cancelled":
            buckets["cancelled"] += 1
        elif r.http_status == 429:
            buckets["429"] += 1
        elif r.http_status == 504:
            buckets["timeout"] += 1
        elif r.http_status >= 500:
            buckets["5xx"] += 1
        elif r.http_status and r.http_status != 200:
            buckets["other"] += 1
    return [{"name": k, "value": v} for k, v in buckets.items()]
