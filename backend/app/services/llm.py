from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.config.settings import settings
from app.net import PublicURLError, assert_public_http_url

# Transient failures worth retrying (rate limit, gateway and overload errors).
RETRY_STATUS = frozenset({408, 409, 429, 500, 502, 503, 504})
MAX_ATTEMPTS = 3
BACKOFF_BASE_SEC = 1.0
MAX_RETRY_AFTER_SEC = 30.0

# Test seams: tests inject an httpx.MockTransport and a no-op sleep.
_transport: httpx.AsyncBaseTransport | None = None
_sleep = asyncio.sleep


class LLMError(RuntimeError):
    """Any failure to obtain a usable completion. The runtime falls back to a plain build."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _base() -> str:
    url = (settings.llm_base_url or "").strip().rstrip("/")
    if not url:
        raise LLMError("未配置 LLM_BASE_URL")
    try:
        return assert_public_http_url(url)
    except PublicURLError as e:
        raise LLMError(str(e)) from e


def _retry_delay(attempt: int, response: Any) -> float:
    headers = getattr(response, "headers", None) or {}
    raw = str(headers.get("retry-after", "")).strip()
    try:
        return min(max(float(raw), 0.0), MAX_RETRY_AFTER_SEC)
    except ValueError:
        return BACKOFF_BASE_SEC * (2**attempt)


async def chat(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    *,
    temperature: float | None = 0.1,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    if not settings.llm_api_key:
        raise LLMError("未配置 LLM_API_KEY")
    if not settings.llm_model:
        raise LLMError("未配置 LLM_MODEL")
    payload: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": messages,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    headers = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}
    url = f"{_base()}/chat/completions"

    last_error = LLMError("LLM 请求失败")
    async with httpx.AsyncClient(timeout=90.0, transport=_transport) as client:
        for attempt in range(MAX_ATTEMPTS):
            response = None
            try:
                response = await client.post(url, json=payload, headers=headers)
            except httpx.TimeoutException as e:
                last_error = LLMError(f"LLM 请求超时: {e}")
            except httpx.TransportError as e:
                last_error = LLMError(f"LLM 网络错误: {e}")
            else:
                if response.status_code < 400:
                    return _parse(response)
                last_error = LLMError(
                    f"LLM HTTP {response.status_code}: {response.text[:300]}", status_code=response.status_code
                )
                if response.status_code not in RETRY_STATUS:
                    raise last_error
            if attempt + 1 < MAX_ATTEMPTS:
                await _sleep(_retry_delay(attempt, response))
    raise last_error


def _parse(response: Any) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError as e:
        raise LLMError(f"LLM 返回的不是 JSON: {response.text[:200]}") from e
    if not isinstance(data, dict) or not data.get("choices"):
        raise LLMError(f"LLM 响应缺少 choices: {str(data)[:200]}")
    return data
