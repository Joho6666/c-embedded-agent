from __future__ import annotations

import pytest

from app.config.settings import settings
from app.services import llm


class _Response:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"choices": []}


@pytest.mark.asyncio
async def test_chat_accepts_explicit_generation_options(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    class _Client:
        def __init__(self, **kwargs) -> None:
            captured["client"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:
            return None

        async def post(self, url: str, **kwargs):
            captured["url"] = url
            captured.update(kwargs)
            return _Response()

    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model", "test-model")
    monkeypatch.setattr(settings, "llm_base_url", "https://example.com/v1")
    monkeypatch.setattr(llm.httpx, "AsyncClient", _Client)
    monkeypatch.setattr(llm, "assert_public_http_url", lambda value: value)

    await llm.chat(
        [{"role": "user", "content": "same task"}],
        temperature=0,
        max_tokens=2048,
    )

    assert captured["json"]["model"] == "test-model"
    assert captured["json"]["temperature"] == 0
    assert captured["json"]["max_tokens"] == 2048


@pytest.mark.asyncio
async def test_chat_default_payload_remains_backwards_compatible(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    class _Client:
        def __init__(self, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:
            return None

        async def post(self, url: str, **kwargs):
            captured.update(kwargs)
            return _Response()

    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model", "test-model")
    monkeypatch.setattr(settings, "llm_base_url", "https://example.com/v1")
    monkeypatch.setattr(llm.httpx, "AsyncClient", _Client)
    monkeypatch.setattr(llm, "assert_public_http_url", lambda value: value)

    await llm.chat([{"role": "user", "content": "existing call"}])

    assert captured["json"]["temperature"] == 0.1
    assert "max_tokens" not in captured["json"]
