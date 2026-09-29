from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.config.settings import settings
from app.net import PublicURLError, assert_public_http_url


class LLMError(RuntimeError):
    pass


_client: httpx.AsyncClient | None = None

# Retry only transient failures; 4xx (except 429) means the request itself is wrong.
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=settings.llm_timeout_sec,
            limits=httpx.Limits(max_connections=8, max_keepalive_connections=4),
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


def _base() -> str:
    url = (settings.llm_base_url or "").strip().rstrip("/")
    if not url:
        raise LLMError("未配置 LLM_BASE_URL")
    try:
        return assert_public_http_url(url)
    except PublicURLError as e:
        raise LLMError(str(e)) from e


def _retry_delay(response: httpx.Response | None, attempt: int) -> float:
    if response is not None:
        raw = response.headers.get("retry-after")
        if raw:
            try:
                return min(30.0, max(0.5, float(raw)))
            except ValueError:
                pass
    return min(8.0, 0.5 * (2**attempt))


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
    url = f"{_base()}/chat/completions"
    client = _get_client()
    max_retries = max(0, settings.llm_max_retries)
    last: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            r = await client.post(url, json=payload, headers=headers)
            if r.status_code in _RETRYABLE_STATUS and attempt < max_retries:
                last = LLMError(f"LLM HTTP {r.status_code}")
                await asyncio.sleep(_retry_delay(r, attempt))
                continue
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            raise LLMError(f"LLM HTTP {e.response.status_code}") from e
        except (httpx.TimeoutException, httpx.TransportError) as e:
            if attempt < max_retries:
                last = e
                await asyncio.sleep(_retry_delay(None, attempt))
                continue
            raise LLMError(f"LLM 请求失败: {e}") from e
    raise LLMError(str(last) if last else "LLM 请求失败")
