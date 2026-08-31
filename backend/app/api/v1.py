from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_gateway_key
from app.gateway.engine import execute_chat, persist_log
from app.models.database import ApiKeyRow, ModelRow, VirtualModelRow
from app.providers.base import UpstreamError

router = APIRouter(prefix="/v1")


@router.get("/models")
def list_models(db: Session = Depends(get_db), key: ApiKeyRow = Depends(require_gateway_key)):
    data = []
    for m in db.query(ModelRow).all():
        data.append({"id": m.model_id, "object": "model", "owned_by": m.provider_id})
    for v in db.query(VirtualModelRow).all():
        data.append({"id": v.slug, "object": "model", "owned_by": "gateway"})
    return {"object": "list", "data": data}


async def _run(db: Session, body: dict[str, Any], key: ApiKeyRow, stream: bool):
    requested = str(body.get("model") or "")
    allowed = json.loads(key.allowed_models or "[]")
    if allowed and requested not in allowed and "*" not in allowed:
        raise HTTPException(status_code=403, detail=f"model '{requested}' not allowed for this key")
    result = await execute_chat(db, body, stream=stream)
    persist_log(db, result, key.id, requested, stream)
    key.requests_today += 1
    key.tokens_today += result.input_tokens + result.output_tokens
    db.flush()
    return result


@router.post("/chat/completions")
async def chat_completions(request: Request, db: Session = Depends(get_db), key: ApiKeyRow = Depends(require_gateway_key)):
    body = await request.json()
    stream = bool(body.get("stream"))
    result = await _run(db, body, key, stream)
    if stream and result.stream_iter is not None:

        async def gen():
            try:
                async for chunk in result.stream_iter:
                    yield chunk
            except UpstreamError as exc:
                err = json.dumps({"error": {"message": exc.message, "type": "upstream_error", "code": exc.status_code}})
                yield f"data: {err}\n\n".encode()
                yield b"data: [DONE]\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")
    if result.payload is None:
        return JSONResponse({"error": {"message": result.error or "upstream failed", "type": "gateway_error"}}, status_code=result.status_code or 502)
    return JSONResponse(result.payload)


@router.post("/responses")
async def responses(request: Request, db: Session = Depends(get_db), key: ApiKeyRow = Depends(require_gateway_key)):
    from app.gateway.engine import candidate_queue, ctx_for, mark_failure, mark_success, persist_log as plog
    from app.models.database import ProviderRow
    from app.providers.registry import get_adapter
    import time

    body = await request.json()
    requested = str(body.get("model") or "")
    allowed = json.loads(key.allowed_models or "[]")
    if allowed and requested not in allowed and "*" not in allowed:
        raise HTTPException(status_code=403, detail=f"model '{requested}' not allowed for this key")
    virtual, _strategy, queue = candidate_queue(db, requested)
    if not queue:
        raise HTTPException(404, "no credential")
    cred, upstream = queue[0]
    provider = db.get(ProviderRow, cred.provider_id)
    adapter = get_adapter(provider.type if provider else "openai_compatible")
    call_body = dict(body)
    call_body["model"] = upstream
    started = time.perf_counter()
    try:
        chat = await adapter.responses(ctx_for(cred), call_body)
        latency = int((time.perf_counter() - started) * 1000)
        mark_success(cred, latency, 0)
        from app.gateway.engine import RouteResult

        result = RouteResult(
            payload=chat.payload,
            status_code=200,
            real_model=upstream,
            provider_id=cred.provider_id,
            credential_id=cred.id,
            virtual_model=virtual,
            latency_ms=latency,
        )
        plog(db, result, key.id, requested, False)
        db.flush()
        return JSONResponse(chat.payload)
    except UpstreamError as exc:
        mark_failure(cred, exc.status_code, exc.message)
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
