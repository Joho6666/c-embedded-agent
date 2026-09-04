from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.providers.base import AdapterContext, BaseProviderAdapter, ChatResult, UpstreamError, retryable_status
from app.providers.transform import chat_body_from_responses, responses_from_chat


class GeminiAdapter(BaseProviderAdapter):
    """Google Generative Language API, OpenAI-shaped on the Gateway side."""

    name = "gemini"
    supports_native_responses = False
    supports_vision = True
    supports_reasoning = True

    def _key(self, ctx: AdapterContext) -> str:
        return ctx.api_key or ctx.headers.get("x-goog-api-key", "")

    def _root(self, ctx: AdapterContext) -> str:
        return (ctx.base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")

    async def list_models(self, ctx: AdapterContext) -> list[str]:
        url = f"{self._root(ctx)}/models"
        async with httpx.AsyncClient(timeout=ctx.timeout_s) as client:
            r = await client.get(url, params={"key": self._key(ctx)})
        if r.status_code >= 400:
            raise UpstreamError(r.status_code, r.text[:500], retryable_status(r.status_code))
        ids = []
        for item in r.json().get("models", []):
            name = str(item.get("name", "")).split("/")[-1]
            if name:
                ids.append(name)
        return ids

    async def health_check(self, ctx: AdapterContext) -> tuple[bool, str, int]:
        try:
            models = await self.list_models(ctx)
            return True, f"ok · {len(models)} models", 200
        except UpstreamError as exc:
            return False, exc.message, exc.status_code
        except Exception as exc:  # noqa: BLE001
            return False, str(exc), 0

    def _to_gemini(self, body: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        model = str(body.get("model", "gemini-2.0-flash"))
        contents = []
        system = ""
        for msg in body.get("messages") or []:
            role = msg.get("role", "user")
            text = msg.get("content", "")
            if isinstance(text, list):
                text = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in text)
            if role == "system":
                system = str(text)
                continue
            contents.append({"role": "user" if role == "user" else "model", "parts": [{"text": str(text)}]})
        payload: dict[str, Any] = {"contents": contents}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        gen: dict[str, Any] = {}
        if body.get("temperature") is not None:
            gen["temperature"] = body["temperature"]
        if body.get("max_tokens") is not None:
            gen["maxOutputTokens"] = body["max_tokens"]
        if gen:
            payload["generationConfig"] = gen
        return model, payload

    def _from_gemini(self, model: str, data: dict[str, Any]) -> dict[str, Any]:
        text = ""
        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts)
        except Exception:  # noqa: BLE001
            text = ""
        usage = data.get("usageMetadata") or {}
        return {
            "id": "gemini-chat",
            "object": "chat.completion",
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": usage.get("promptTokenCount", 0),
                "completion_tokens": usage.get("candidatesTokenCount", 0),
                "total_tokens": usage.get("totalTokenCount", 0),
            },
        }

    async def chat_completion(self, ctx: AdapterContext, body: dict[str, Any]) -> ChatResult:
        model, payload = self._to_gemini(body)
        url = f"{self._root(ctx)}/models/{model}:generateContent"
        async with httpx.AsyncClient(timeout=ctx.timeout_s) as client:
            r = await client.post(url, params={"key": self._key(ctx)}, json=payload)
        if r.status_code >= 400:
            raise UpstreamError(r.status_code, r.text[:800], retryable_status(r.status_code))
        return ChatResult(status_code=200, payload=self._from_gemini(model, r.json()))

    async def stream_chat_completion(self, ctx: AdapterContext, body: dict[str, Any]) -> AsyncIterator[bytes]:
        model, payload = self._to_gemini(body)
        url = f"{self._root(ctx)}/models/{model}:streamGenerateContent"
        async with httpx.AsyncClient(timeout=ctx.timeout_s) as client:
            async with client.stream(
                "POST",
                url,
                params={"key": self._key(ctx), "alt": "sse"},
                json=payload,
            ) as r:
                if r.status_code >= 400:
                    text = (await r.aread()).decode("utf-8", errors="replace")[:800]
                    raise UpstreamError(r.status_code, text, retryable_status(r.status_code))
                async for line in r.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if not raw or raw == "[DONE]":
                        continue
                    import json

                    try:
                        obj = json.loads(raw)
                        piece = obj["candidates"][0]["content"]["parts"][0].get("text", "")
                    except Exception:  # noqa: BLE001
                        continue
                    chunk = {
                        "id": "gemini-chunk",
                        "object": "chat.completion.chunk",
                        "model": model,
                        "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}],
                    }
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode("utf-8")
                yield b"data: [DONE]\n\n"

    async def responses(self, ctx: AdapterContext, body: dict[str, Any]) -> ChatResult:
        result = await self.chat_completion(ctx, chat_body_from_responses(body))
        return responses_from_chat(result)
