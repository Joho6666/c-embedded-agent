from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_gateway_key
from app.core.database import SessionLocal
from app.gateway.engine import begin_log, execute_chat, execute_responses, persist_log
from app.gateway.quota import check_key_quota, quota_error, record_key_usage
from app.models.database import ApiKeyRow, ModelRow, VirtualModelRow
from app.providers.base import UpstreamError

router = APIRouter(prefix="/v1")


def error_response(code: str, message: str, status: int = 429, err_type: str = "rate_limit_error") -> JSONResponse:
    return JSONResponse({"error": {"message": message, "type": err_type, "code": code}}, status_code=status)


def result_error(result) -> JSONResponse:
    code = result.error_code or "upstream_error"
    err_type = "rate_limit_error" if code.endswith("exceeded") or "quota" in code else "gateway_error"
    return JSONResponse(
        {"error": {"message": result.error or "upstream failed", "type": err_type, "code": code}},
        status_code=result.status_code or 502,
    )


@router.get("/models")
def list_models(db: Session = Depends(get_db), key: ApiKeyRow = Depends(require_gateway_key)):
    data = []
    for m in db.query(ModelRow).all():
        data.append({"id": m.model_id, "object": "model", "owned_by": m.provider_id})
    for v in db.query(VirtualModelRow).all():
        data.append({"id": v.slug, "object": "model", "owned_by": "gateway"})
    return {"object": "list", "data": data}


def _check_model(key: ApiKeyRow, requested: str) -> JSONResponse | None:
    allowed = json.loads(key.allowed_models or "[]")
    if allowed and requested not in allowed and "*" not in allowed:
        packed = quota_error("model_not_allowed", f"model '{requested}' not allowed for this key", status=403)
        return JSONResponse(packed["body"], status_code=403)
    return None


async def _prepare(db: Session, body: dict[str, Any], key: ApiKeyRow, stream: bool):
    requested = str(body.get("model") or "")
    blocked = _check_model(key, requested)
    if blocked is not None:
        return blocked, None, None
    limited = check_key_quota(key, body)
    if limited is not None:
        return JSONResponse(limited["body"], status_code=limited["status"]), None, None
    log = begin_log(db, key.id, requested, stream, "")
    db.commit()
    log_id = log.id
    db.expunge(log)
    return None, log_id, requested


@router.post("/chat/completions")
async def chat_completions(request: Request, db: Session = Depends(get_db), key: ApiKeyRow = Depends(require_gateway_key)):
    body = await request.json()
    stream = bool(body.get("stream"))
    early, log_id, requested = await _prepare(db, body, key, stream)
    if early is not None:
        return early
    assert log_id is not None and requested is not None
    result = await execute_chat(db, body, stream=stream, log_id=log_id)
    result.log_id = log_id
    if not result.virtual_model:
        result.virtual_model = result.virtual_model or requested

    if stream and result.stream_iter is not None:
        key_id = key.id
        requested_model = requested

        async def gen():
            try:
                async for chunk in result.stream_iter:
                    if await request.is_disconnected():
                        result.client_disconnected = True
                        result.request_status = "cancelled"
                        result.error = "client disconnected"
                        result.error_code = "cancelled"
                        break
                    yield chunk
            except asyncio.CancelledError:
                result.client_disconnected = True
                result.request_status = "cancelled"
                result.error = "client disconnected"
                result.error_code = "cancelled"
                raise
            except UpstreamError as exc:
                result.status_code = exc.status_code or 502
                result.error = exc.message
                result.request_status = "error"
                err = json.dumps({"error": {"message": exc.message, "type": "upstream_error", "code": str(exc.status_code)}})
                yield f"data: {err}\n\n".encode()
                yield b"data: [DONE]\n\n"
            finally:
                s = SessionLocal()
                try:
                    persist_log(s, result, key_id, requested_model, True)
                    krow = s.get(ApiKeyRow, key_id)
                    if krow:
                        record_key_usage(s, krow, result.input_tokens + result.output_tokens, result.estimated_cost)
                    s.commit()
                except Exception:
                    s.rollback()
                    raise
                finally:
                    s.close()

        return StreamingResponse(gen(), media_type="text/event-stream")

    persist_log(db, result, key.id, requested, False)
    record_key_usage(db, key, result.input_tokens + result.output_tokens, result.estimated_cost)
    if result.payload is None:
        return result_error(result)
    return JSONResponse(result.payload)


@router.post("/responses")
async def responses(request: Request, db: Session = Depends(get_db), key: ApiKeyRow = Depends(require_gateway_key)):
    body = await request.json()
    stream = bool(body.get("stream"))
    early, log_id, requested = await _prepare(db, body, key, stream)
    if early is not None:
        return early
    assert log_id is not None and requested is not None
    result = await execute_responses(db, body, stream=stream, log_id=log_id)
    result.log_id = log_id

    if stream and result.stream_iter is not None:
        key_id = key.id

        async def gen():
            try:
                async for chunk in result.stream_iter:
                    if await request.is_disconnected():
                        result.client_disconnected = True
                        result.request_status = "cancelled"
                        break
                    yield chunk
            except asyncio.CancelledError:
                result.client_disconnected = True
                result.request_status = "cancelled"
                raise
            except UpstreamError as exc:
                result.status_code = exc.status_code or 502
                result.error = exc.message
                result.request_status = "error"
                err = json.dumps({"error": {"message": exc.message, "type": "upstream_error", "code": str(exc.status_code)}})
                yield f"data: {err}\n\n".encode()
                yield b"data: [DONE]\n\n"
            finally:
                s = SessionLocal()
                try:
                    persist_log(s, result, key_id, requested, True)
                    krow = s.get(ApiKeyRow, key_id)
                    if krow:
                        record_key_usage(s, krow, result.input_tokens + result.output_tokens, result.estimated_cost)
                    s.commit()
                except Exception:
                    s.rollback()
                finally:
                    s.close()

        return StreamingResponse(gen(), media_type="text/event-stream")

    persist_log(db, result, key.id, requested, False)
    record_key_usage(db, key, result.input_tokens + result.output_tokens, result.estimated_cost)
    if result.payload is None:
        return result_error(result)
    return JSONResponse(result.payload)
