from __future__ import annotations

import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import admin_auth, get_db
from app.api.serializers import credential_out, key_out, log_out, model_out, provider_out, virtual_out
from app.core.ids import new_id
from app.core.security import encrypt_secret, generate_gateway_key, hash_api_key
from app.gateway.engine import ctx_for, maybe_recover_circuit
from app.models.database import (
    ApiKeyRow,
    CredentialRow,
    ModelRow,
    ProviderRow,
    RequestLogRow,
    VirtualModelRow,
    utcnow,
)
from app.providers.registry import get_adapter

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
    monthlyBudget: float = 40
    ipWhitelist: list[str] = Field(default_factory=list)


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
    row = ProviderRow(
        id=pid,
        name=body.name or name,
        type=ptype,
        descriptor_id=desc,
        base_url=body.baseUrl or base,
        family=family,
        color=color,
        mark=mark,
        capabilities=json.dumps(["chat", "streaming", "responses"]),
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
    ok, msg, code = await adapter.health_check(ctx_for(cred))
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
    ids = await adapter.list_models(ctx_for(cred))
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
    ok, msg, code = await adapter.health_check(ctx_for(row))
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
        "estimatedCost": 0,
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
        healthy = all(c.status in {"healthy", "rate_limited"} for c in pc) if pc else True
        providers.append(
            {
                "providerId": p.id,
                "status": "operational" if healthy else "degraded",
                "latencyMs": int(sum(c.avg_latency_ms for c in pc) / len(pc)) if pc else 0,
                "successRate": 100,
            }
        )
    overall = "operational" if counts.get("circuit_open", 0) == 0 else "degraded"
    return {
        "overall": overall,
        "checkedAt": utcnow().isoformat() + "Z",
        "components": [
            {"id": "gateway", "name": "Gateway", "status": "operational", "detail": "FastAPI"},
            {"id": "database", "name": "Database", "status": "operational", "detail": "SQLite"},
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
