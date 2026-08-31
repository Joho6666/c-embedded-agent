from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urljoin

import httpx

from app.providers.base import AdapterContext, BaseProviderAdapter, ChatResult, UpstreamError, retryable_status
from app.providers.transform import chat_body_from_responses, responses_from_chat


def _join(base: str, path: str) -> str:
    base = base.rstrip("/") + "/"
    return urljoin(base, path.lstrip("/"))


class OpenAICompatibleAdapter(BaseProviderAdapter):
    name = "openai_compatible"

    def _headers(self, ctx: AdapterContext) -> dict[str, str]:
        headers = {"Content-Type": "application/json", **ctx.headers}
        if ctx.api_key and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {ctx.api_key}"
        return headers

    async def list_models(self, ctx: AdapterContext) -> list[str]:
        url = _join(ctx.base_url, "/models")
        async with httpx.AsyncClient(timeout=ctx.timeout_s) as client:
            r = await client.get(url, headers=self._headers(ctx))
        if r.status_code >= 400:
            raise UpstreamError(r.status_code, r.text[:500], retryable_status(r.status_code))
        data = r.json()
        items = data.get("data") if isinstance(data, dict) else data
        ids: list[str] = []
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and item.get("id"):
                    ids.append(str(item["id"]))
                elif isinstance(item, str):
                    ids.append(item)
        return ids

    async def health_check(self, ctx: AdapterContext) -> tuple[bool, str, int]:
        try:
            models = await self.list_models(ctx)
            return True, f"ok · {len(models)} models", 200
        except UpstreamError as exc:
            return False, exc.message, exc.status_code
        except Exception as exc:  # noqa: BLE001
            return False, str(exc), 0

    async def chat_completion(self, ctx: AdapterContext, body: dict[str, Any]) -> ChatResult:
        payload = self.normalize_request(body)
        payload["stream"] = False
        url = _join(ctx.base_url, "/chat/completions")
        async with httpx.AsyncClient(timeout=ctx.timeout_s) as client:
            r = await client.post(url, headers=self._headers(ctx), json=payload)
        if r.status_code >= 400:
            raise UpstreamError(r.status_code, r.text[:800], retryable_status(r.status_code))
        return ChatResult(status_code=r.status_code, payload=self.normalize_response(r.json()))

    async def stream_chat_completion(self, ctx: AdapterContext, body: dict[str, Any]) -> AsyncIterator[bytes]:
        payload = self.normalize_request(body)
        payload["stream"] = True
        url = _join(ctx.base_url, "/chat/completions")
        headers = self._headers(ctx)
        headers["Accept"] = "text/event-stream"
        async with httpx.AsyncClient(timeout=ctx.timeout_s) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as r:
                if r.status_code >= 400:
                    text = (await r.aread()).decode("utf-8", errors="replace")[:800]
                    raise UpstreamError(r.status_code, text, retryable_status(r.status_code))
                async for chunk in r.aiter_bytes():
                    if chunk:
                        yield chunk

    async def responses(self, ctx: AdapterContext, body: dict[str, Any]) -> ChatResult:
        url = _join(ctx.base_url, "/responses")
        async with httpx.AsyncClient(timeout=ctx.timeout_s) as client:
            r = await client.post(url, headers=self._headers(ctx), json=body)
        if r.status_code == 404:
            return await self._responses_via_chat(ctx, body)
        if r.status_code >= 400:
            raise UpstreamError(r.status_code, r.text[:800], retryable_status(r.status_code))
        return ChatResult(status_code=r.status_code, payload=r.json())

    async def _responses_via_chat(self, ctx: AdapterContext, body: dict[str, Any]) -> ChatResult:
        result = await self.chat_completion(ctx, chat_body_from_responses(body))
        return responses_from_chat(result)
