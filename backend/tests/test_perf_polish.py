"""Performance polish guards: knowledge fingerprint, schema-once, LLM retry,
context aging, RUNS eviction, serial timestamps."""

from __future__ import annotations

import uuid
from pathlib import Path

import httpx
import pytest

from app.config.settings import settings


# ---------------------------------------------------------------- knowledge FTS guard


@pytest.fixture()
def fresh_knowledge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "workspace_root", tmp_path / "ws")
    kroot = tmp_path / "kb"
    kroot.mkdir()
    monkeypatch.setattr(settings, "knowledge_root", kroot)
    import app.tools.knowledge as knowledge

    knowledge._ingested_fingerprint = None
    yield knowledge, kroot
    knowledge._ingested_fingerprint = None


def test_knowledge_skips_reingest_until_dir_changes(fresh_knowledge, monkeypatch):
    knowledge, kroot = fresh_knowledge
    (kroot / "gpio.md").write_text("---\ntitle: GPIO\n---\nGPIO PC13 note", encoding="utf-8")
    calls = {"n": 0}
    real = knowledge.ingest_markdown

    def counting() -> int:
        calls["n"] += 1
        return real()

    monkeypatch.setattr(knowledge, "ingest_markdown", counting)
    assert knowledge.retrieve_knowledge("GPIO")
    assert calls["n"] == 1
    # unchanged dir → cached fingerprint, no FTS rebuild
    assert knowledge.retrieve_knowledge("GPIO")
    assert calls["n"] == 1
    # changed content → rebuild
    (kroot / "gpio.md").write_text("---\ntitle: GPIO\n---\nGPIO PC13 extended AFIO note", encoding="utf-8")
    assert knowledge.retrieve_knowledge("GPIO")
    assert calls["n"] == 2


# ---------------------------------------------------------------- db schema-once


def test_connect_skips_schema_on_hot_path(tmp_path, monkeypatch):
    from app import db as db_mod

    monkeypatch.setattr(settings, "workspace_root", tmp_path)
    db_mod._schema_ready_for = None
    try:
        con = db_mod.connect()
        con.execute("DROP TABLE runs")
        con.commit()
        con.close()
        # second connect must not re-run the schema script, so `runs` stays dropped
        con2 = db_mod.connect()
        tables = {r[0] for r in con2.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        con2.close()
        assert "runs" not in tables
    finally:
        db_mod._schema_ready_for = None


def test_connect_reinitializes_for_new_workspace(tmp_path, monkeypatch):
    from app import db as db_mod

    db_mod._schema_ready_for = None
    try:
        monkeypatch.setattr(settings, "workspace_root", tmp_path / "a")
        con = db_mod.connect()
        con.close()
        assert db_mod._schema_ready_for == db_mod.db_path()
        monkeypatch.setattr(settings, "workspace_root", tmp_path / "b")
        con = db_mod.connect()
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        con.close()
        assert "runs" in tables  # fresh db got its schema
    finally:
        db_mod._schema_ready_for = None


# ---------------------------------------------------------------- LLM retry


@pytest.fixture()
def llm_env(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model", "test-model")
    monkeypatch.setattr(settings, "llm_base_url", "https://llm.example.com/v1")
    monkeypatch.setattr(settings, "llm_max_retries", 2)


def _install_transport(monkeypatch, handler):
    from app.services import llm

    calls = []

    def counting_handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return handler(request)

    monkeypatch.setattr(llm, "_client", httpx.AsyncClient(transport=httpx.MockTransport(counting_handler)))
    monkeypatch.setattr(llm, "_base", lambda: "https://mock-llm.local/v1")
    delays: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        delays.append(seconds)

    monkeypatch.setattr(llm.asyncio, "sleep", _fake_sleep)
    return calls, delays


def test_llm_retries_on_500_then_succeeds(llm_env, monkeypatch):
    from app.services import llm

    state = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["n"] += 1
        if state["n"] == 1:
            return httpx.Response(500, json={"error": "boom"})
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}], "usage": {}})

    calls, _ = _install_transport(monkeypatch, handler)

    async def _run():
        return await llm.chat([{"role": "user", "content": "hi"}])

    import asyncio

    data = asyncio.run(_run())
    assert data["choices"][0]["message"]["content"] == "ok"
    assert len(calls) == 2


def test_llm_respects_retry_after_header(llm_env, monkeypatch):
    from app.services import llm

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"retry-after": "3"}, json={})

    calls, delays = _install_transport(monkeypatch, handler)

    def always_500(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={})

    async def _run():
        await llm.chat([{"role": "user", "content": "hi"}])

    import asyncio

    with pytest.raises(llm.LLMError):
        asyncio.run(_run())
    assert delays and delays[0] == 3.0


def test_llm_no_retry_on_client_error(llm_env, monkeypatch):
    from app.services import llm

    calls, _ = _install_transport(monkeypatch, lambda request: httpx.Response(400, json={}))

    async def _run():
        await llm.chat([{"role": "user", "content": "hi"}])

    import asyncio

    with pytest.raises(llm.LLMError):
        asyncio.run(_run())
    assert len(calls) == 1


def test_llm_exhausts_retries(llm_env, monkeypatch):
    from app.services import llm

    calls, _ = _install_transport(monkeypatch, lambda request: httpx.Response(503, json={}))

    async def _run():
        await llm.chat([{"role": "user", "content": "hi"}])

    import asyncio

    with pytest.raises(llm.LLMError):
        asyncio.run(_run())
    assert len(calls) == settings.llm_max_retries + 1


# ---------------------------------------------------------------- context aging


def test_age_tool_results_trims_only_old_entries():
    from app.agent.runtime import _age_tool_results

    long = "x" * 3000
    messages: list[dict] = [{"role": "user", "content": "task"}]
    messages += [{"role": "tool", "tool_call_id": str(i), "content": long} for i in range(6)]
    _age_tool_results(messages)
    tools = [m for m in messages if m["role"] == "tool"]
    for m in tools[-settings.tool_history_keep:]:
        assert m["content"] == long
    for m in tools[:-settings.tool_history_keep]:
        assert m["content"].endswith("…(历史结果已截断)")
        assert len(m["content"]) == settings.old_tool_result_chars + len("…(历史结果已截断)")


def test_age_tool_results_ignores_short_results():
    from app.agent.runtime import _age_tool_results

    messages = [{"role": "tool", "tool_call_id": str(i), "content": "short"} for i in range(6)]
    _age_tool_results(messages)
    assert all(m["content"] == "short" for m in messages)


# ---------------------------------------------------------------- RUNS eviction


def test_evict_finished_runs_keeps_running():
    from app.agent import runtime

    runtime.RUNS.clear()
    try:
        keep = runtime.AgentRun(f"run-{uuid.uuid4().hex[:8]}", "p", "prompt", "auto")
        keep.status = "running"
        runtime.RUNS[keep.id] = keep
        for _ in range(runtime.MAX_TRACKED_RUNS + 50):
            r = runtime.AgentRun(f"run-{uuid.uuid4().hex[:8]}", "p", "prompt", "auto")
            r.status = "success"
            runtime.RUNS[r.id] = r
        runtime._evict_finished_runs()
        assert len(runtime.RUNS) <= runtime.MAX_TRACKED_RUNS
        assert keep.id in runtime.RUNS
    finally:
        runtime.RUNS.clear()


# ---------------------------------------------------------------- serial timestamps


def test_fmt_elapsed_formats_minutes_seconds():
    from app.agent.runtime import _fmt_elapsed

    assert _fmt_elapsed(0) == "[00:00.00]"
    assert _fmt_elapsed(5.128) == "[00:05.13]"
    assert _fmt_elapsed(62.5) == "[01:02.50]"


def test_timed_lines_computes_real_offsets():
    from app.tools import serialutil

    rows = serialutil._session["lines"]
    rows.clear()
    try:
        serialutil._session["started"] = 100.0
        rows.append({"text": "hello", "t": 101.5})
        rows.append({"text": "world", "t": 103.25})
        rows.append({"text": "legacy"})  # pre-polish row without timestamp
        timed = serialutil.timed_lines()
        assert timed[0] == ("hello", 1.5)
        assert timed[1] == ("world", 3.25)
        assert timed[2] == ("legacy", 0.0)
    finally:
        rows.clear()


# ---------------------------------------------------------------- context message replacement


def test_llm_loop_keeps_single_context_message_across_iterations(tmp_path, monkeypatch):
    import asyncio

    from app.agent import runtime

    (tmp_path / "Core" / "Src").mkdir(parents=True)
    seen: list[list[dict]] = []

    async def fake_chat(messages, tools=None):
        seen.append([dict(m) for m in messages])
        if len(seen) == 1:
            return {
                "choices": [{
                    "message": {
                        "content": "",
                        "tool_calls": [{"id": "t1", "function": {"name": "list_files", "arguments": "{}"}}],
                    }
                }],
                "usage": {},
            }
        return {"choices": [{"message": {"content": "done", "tool_calls": []}}], "usage": {}}

    async def fake_compile(run, root):
        return {"success": True, "combined": "", "diagnostics": [], "artifacts": []}

    monkeypatch.setattr(runtime, "chat", fake_chat)
    monkeypatch.setattr(runtime, "_compile", fake_compile)
    run = runtime.AgentRun("r-ctx", "p", "LED blink", "auto")
    asyncio.run(runtime._llm_loop(run, tmp_path, {"board": "Blue Pill"}))

    assert len(seen) == 2
    for msgs in seen:
        ctx = [m for m in msgs if m.get("role") == "system" and str(m.get("content", "")).startswith("当前上下文")]
        assert len(ctx) == 1  # replaced in place, never accumulated
