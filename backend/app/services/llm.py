from __future__ import annotations

from typing import Any

import httpx

from app.config.settings import settings
from app.net import PublicURLError, assert_public_http_url


class LLMError(RuntimeError):
    pass


def _base() -> str:
    url = (settings.llm_base_url or "").strip().rstrip("/")
    if not url:
        raise LLMError("未配置 LLM_BASE_URL")
    try:
        return assert_public_http_url(url)
    except PublicURLError as e:
        raise LLMError(str(e)) from e


async def chat(messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if not settings.llm_api_key:
        raise LLMError("未配置 LLM_API_KEY")
    if not settings.llm_model:
        raise LLMError("未配置 LLM_MODEL")
    payload: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": 0.1,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    headers = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=90.0) as client:
        r = await client.post(f"{_base()}/chat/completions", json=payload, headers=headers)
        r.raise_for_status()
        return r.json()
