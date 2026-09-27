"""LLM transport failures are normalised to LLMError, retried when transient,
and make the runtime fall back to a plain build instead of a generic crash."""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest

from app.agent import runtime
from app.config.settings import settings
from app.services import llm

OK = {"choices": [{"message": {"role": "assistant", "content": "ok"}}]}


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model", "test-model")
    monkeypatch.setattr(settings, "llm_base_url", "https://example.com/v1")
    monkeypatch.setattr(llm, "assert_public_http_url", lambda value: value)
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(llm, "_sleep", fake_sleep)
    return sleeps


def _transport(monkeypatch, responses: list) -> list[httpx.Request]:
    seen: list[httpx.Request] = []
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(llm, "_transport", httpx.MockTransport(handler))
    return seen


def test_rate_limit_is_retried_honouring_retry_after(configured, monkeypatch):
    seen = _transport(monkeypatch, [httpx.Response(429, headers={"Retry-After": "2"}), httpx.Response(200, json=OK)])
    data = asyncio.run(llm.chat([{"role": "user", "content": "hi"}]))
    assert data["choices"][0]["message"]["content"] == "ok"
    assert len(seen) == 2
    assert configured == [2.0]


def test_persistent_server_error_raises_llm_error(configured, monkeypatch):
    seen = _transport(monkeypatch, [httpx.Response(500, text="boom")] * llm.MAX_ATTEMPTS)
    with pytest.raises(llm.LLMError) as exc:
        asyncio.run(llm.chat([{"role": "user", "content": "hi"}]))
    assert exc.value.status_code == 500
    assert len(seen) == llm.MAX_ATTEMPTS
    assert configured == [1.0, 2.0]


def test_auth_error_is_not_retried(configured, monkeypatch):
    seen = _transport(monkeypatch, [httpx.Response(401, text="bad key")])
    with pytest.raises(llm.LLMError) as exc:
        asyncio.run(llm.chat([{"role": "user", "content": "hi"}]))
    assert exc.value.status_code == 401
    assert len(seen) == 1


def test_network_error_and_bad_body_become_llm_error(configured, monkeypatch):
    _transport(monkeypatch, [httpx.ConnectError("refused")] * llm.MAX_ATTEMPTS)
    with pytest.raises(llm.LLMError):
        asyncio.run(llm.chat([{"role": "user", "content": "hi"}]))
    _transport(monkeypatch, [httpx.Response(200, text="<html>gateway</html>")])
    with pytest.raises(llm.LLMError):
        asyncio.run(llm.chat([{"role": "user", "content": "hi"}]))


def test_runtime_falls_back_to_build_when_llm_fails(tmp_path: Path, monkeypatch):
    from tests.test_runtime_platform_boundary import RecordingAdapter

    adapter = RecordingAdapter(tmp_path)

    class Resolution:
        status = "resolved"
        reason = None

        def __init__(self):
            self.adapter = adapter

    class Registry:
        def detect(self, root):
            return Resolution()

    async def failing_chat(messages, tools):
        raise llm.LLMError("LLM HTTP 503: overloaded", status_code=503)

    compiled: list[bool] = []

    async def fake_compile(run, root, selected):
        compiled.append(True)
        run.emit(type="compile", status="success", title="构建成功")
        run.emit(type="test", status="success", title="cppcheck Unavailable")
        return {"success": False}

    monkeypatch.setattr(runtime, "project_root", lambda project_id: tmp_path)
    monkeypatch.setattr(runtime, "default_registry", lambda root: Registry())
    monkeypatch.setattr(runtime, "snapshot", lambda root, message: "abc")
    monkeypatch.setattr(runtime, "save_run", lambda *a, **k: None)
    monkeypatch.setattr(runtime, "finish_run", lambda *a, **k: None)
    monkeypatch.setattr(runtime, "save_event", lambda *a, **k: None)
    monkeypatch.setattr(runtime, "save_model_call", lambda *a, **k: None)
    monkeypatch.setattr(runtime.AgentRun, "save_checkpoint", lambda self: None)
    monkeypatch.setattr(runtime, "chat", failing_chat)
    monkeypatch.setattr(runtime, "_compile", fake_compile)

    run = runtime.AgentRun("llm-fallback", "p1", "blink LED", "auto")
    asyncio.run(runtime.run_agent(run))

    assert compiled == [True]
    titles = [e["title"] for e in run.events]
    assert "LLM 不可用" in titles and "Agent 异常" not in titles
    # Status comes from the build result, not from whichever event happened to be last.
    assert run.status == "failed"
    assert run.events[-1]["type"] == "run_finished"
