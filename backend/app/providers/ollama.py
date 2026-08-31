from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.providers.base import AdapterContext, ChatResult, UpstreamError, retryable_status
from app.providers.openai_compatible import OpenAICompatibleAdapter


class OllamaAdapter(OpenAICompatibleAdapter):
    name = "ollama"

    def _root(self, ctx: AdapterContext) -> str:
        return (ctx.base_url or "http://localhost:11434").rstrip("/")

    async def list_models(self, ctx: AdapterContext) -> list[str]:
        url = f"{self._root(ctx)}/api/tags"
        async with httpx.AsyncClient(timeout=ctx.timeout_s) as client:
            r = await client.get(url)
        if r.status_code >= 400:
            # fallback OpenAI compatible /v1/models
            try:
                return await super().list_models(ctx)
            except Exception as exc:  # noqa: BLE001
                raise UpstreamError(r.status_code, r.text[:500], retryable_status(r.status_code)) from exc
        names = []
        for item in r.json().get("models", []):
            name = item.get("name") or item.get("model")
            if name:
                names.append(str(name))
        return names

    async def chat_completion(self, ctx: AdapterContext, body: dict[str, Any]) -> ChatResult:
        ctx = AdapterContext(
            base_url=self._openai_base(ctx),
            api_key=ctx.api_key or "ollama",
            headers=ctx.headers,
            timeout_s=ctx.timeout_s,
        )
        return await super().chat_completion(ctx, body)

    async def stream_chat_completion(self, ctx: AdapterContext, body: dict[str, Any]) -> AsyncIterator[bytes]:
        ctx = AdapterContext(
            base_url=self._openai_base(ctx),
            api_key=ctx.api_key or "ollama",
            headers=ctx.headers,
            timeout_s=ctx.timeout_s,
        )
        async for chunk in super().stream_chat_completion(ctx, body):
            yield chunk

    def _openai_base(self, ctx: AdapterContext) -> str:
        base = self._root(ctx)
        if base.endswith("/v1"):
            return base
        return base + "/v1"
