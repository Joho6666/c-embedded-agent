from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_gateway_key
from app.core.database import SessionLocal
from app.core.limiter import allow as rpm_allow
from app.gateway.engine import execute_chat, persist_log, reset_daily_key
from app.models.database import ApiKeyRow, ModelRow, VirtualModelRow
from app.providers.base import ChatResult, UpstreamError
from app.providers.transform import chat_body_from_responses, responses_from_chat

router = APIRouter(prefix="/v1")


def rate_limit_response(code: str) -> JSONResponse:
    return JSONResponse({"error": {"type": "rate_limit_error", "code": code}}, status_code=429)


@router.get("/models")
def list_models(db: Session = Depends(get_db), key: ApiKeyRow = Depends(require_gateway_key)):
    data = []
    for m in db.query(ModelRow).all():
        data.append({"id": m.model_id, "object": "model", "owned_by": m.provider_id})
    for v in db.query(VirtualModelRow).all():
        data.append({"id": v.slug, "object": "model", "owned_by": "gateway"})
    return {"object": "list", "data": data}


def _check_model(key: ApiKeyRow, requested: str) -> None:
    allowed = json.loads(key.allowed_models or "[]")
    if allowed and requested not in allowed and "*" not in allowed:
        raise HTTPException(status_code=403, detail=f"model '{requested}' not allowed for this key")


def _check_key_quota(key: ApiKeyRow) -> JSONResponse | None:
    reset_daily_key(key)
    if key.daily_token_limit and key.tokens_today >= key.daily_token_limit:
        return rate_limit_response("daily_token_exceeded")
    if not rpm_allow(f"key-rpm:{key.id}", key.rpm_limit):
        return rate_limit_response("rpm_exceeded")
    return None


def _bump_key(db: Session, key: ApiKeyRow, tokens: int) -> None:
    reset_daily_key(key)
    key.requests_today += 1
    key.tokens_today += tokens
    db.flush()


async def _execute(db: Session, body: dict[str, Any], key: ApiKeyRow, stream: bool):
    requested = str(body.get("model") or "")
    _check_model(key, requested)
    limited = _check_key_quota(key)
    if limited is not None:
        return limited
    return await execute_chat(db, body, stream=stream)


@router.post("/chat/completions")
async def chat_completions(request: Request, db: Session = Depends(get_db), key: ApiKeyRow = Depends(require_gateway_key)):
    body = await request.json()
    stream = bool(body.get("stream"))
    requested = str(body.get("model") or "")
    result = await _execute(db, body, key, stream)
    if isinstance(result, JSONResponse):
        return result

    if stream and result.stream_iter is not None:
        key_id = key.id

        async def gen():
            try:
                async for chunk in result.stream_iter:
                    yield chunk
            except UpstreamError as exc:
                result.status_code = exc.status_code or 502
                result.error = exc.message
                result.request_status = "error"
                err = json.dumps({"error": {"message": exc.message, "type": "upstream_error", "code": exc.status_code}})
                yield f"data: {err}\n\n".encode()
                yield b"data: [DONE]\n\n"
            finally:
                s = SessionLocal()
                try:
                    persist_log(s, result, key_id, requested, True)
                    krow = s.get(ApiKeyRow, key_id)
                    if krow:
                        _bump_key(s, krow, result.input_tokens + result.output_tokens)
                    s.commit()
                except Exception:
                    s.rollback()
                finally:
                    s.close()

        return StreamingResponse(gen(), media_type="text/event-stream")

    persist_log(db, result, key.id, requested, False)
    _bump_key(db, key, result.input_tokens + result.output_tokens)
    if result.payload is None:
        return JSONResponse(
            {"error": {"message": result.error or "upstream failed", "type": "gateway_error"}},
            status_code=result.status_code or 502,
        )
    return JSONResponse(result.payload)


@router.post("/responses")
async def responses(request: Request, db: Session = Depends(get_db), key: ApiKeyRow = Depends(require_gateway_key)):
    body = await request.json()
    requested = str(body.get("model") or "")
    chat_body = chat_body_from_responses(body)
    chat_body.setdefault("model", requested)
    result = await _execute(db, chat_body, key, False)
    if isinstance(result, JSONResponse):
        return result
    persist_log(db, result, key.id, requested, False)
    _bump_key(db, key, result.input_tokens + result.output_tokens)
    if result.payload is None:
        raise HTTPException(status_code=result.status_code or 502, detail=result.error or "upstream failed")
    transformed = responses_from_chat(ChatResult(status_code=200, payload=result.payload))
    return JSONResponse(transformed.payload)
