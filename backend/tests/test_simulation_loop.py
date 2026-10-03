"""The agent keeps its loop open after a successful build when the task has
observable behaviour, so it can simulate, see a behavioural failure, fix and
re-verify — and a failed simulation fails the run."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from app.agent import runtime
from app.platforms.base import PlatformResult
from app.tools.registry import default_tool_registry
from tests.test_runtime_platform_boundary import RecordingAdapter


class SimAdapter(RecordingAdapter):
    def __init__(self, root: Path, verdicts: list[str]) -> None:
        super().__init__(root)
        self.verdicts = list(verdicts)
        self.specs: list[dict] = []

    def simulate(self, root: Path, spec) -> PlatformResult:
        self.specs.append(dict(spec))
        status = self.verdicts.pop(0)
        reason = None if status == "PASS" else "LED PC13: State duration was out of specified range"
        return PlatformResult(status, "simulate", self.adapter_id, {"checks": [], "kind": "SIMULATED"}, reason=reason)


def _call(call_id: str, name: str, args: dict) -> dict:
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


def _reply(*calls: dict) -> dict:
    message = {"role": "assistant", "content": None if calls else "done"}
    if calls:
        message["tool_calls"] = list(calls)
    return {"choices": [{"message": message}]}


LED_SPEC = {"led": [{"pin": "PC13", "on_ms": 500, "off_ms": 500}]}


def _run(tmp_path: Path, monkeypatch, adapter: SimAdapter, replies: list[dict]) -> runtime.AgentRun:
    (tmp_path / "Core" / "Src").mkdir(parents=True)
    (tmp_path / "Core" / "Src" / "main.c").write_text("HAL_Delay(250);\n", encoding="utf-8")
    queue = list(replies)

    async def fake_chat(messages, tools):
        return queue.pop(0)

    compiles: list[int] = []

    async def fake_compile(run, root, selected):
        compiles.append(1)
        return {"success": True}

    monkeypatch.setattr(runtime, "chat", fake_chat)
    monkeypatch.setattr(runtime, "_compile", fake_compile)
    for name in ("save_model_call", "save_event", "save_file_change"):
        monkeypatch.setattr(runtime, name, lambda *a, **k: None)
    monkeypatch.setattr(runtime.AgentRun, "save_checkpoint", lambda self: None)

    run = runtime.AgentRun("sim-loop", "p1", "PC13 LED 每 500ms 翻转一次", "auto")
    asyncio.run(runtime._llm_loop(run, tmp_path, adapter, SimpleNamespace(hardware_intent=False), default_tool_registry().schemas()))
    assert not queue, "agent stopped before consuming the scripted replies"
    return run


def test_build_does_not_end_the_loop_and_fix_is_reverified(tmp_path: Path, monkeypatch) -> None:
    adapter = SimAdapter(tmp_path, ["FAIL", "PASS"])
    patch = "@@ -1 +1 @@\n-HAL_Delay(250);\n+HAL_Delay(500);\n"
    run = _run(
        tmp_path,
        monkeypatch,
        adapter,
        [
            _reply(_call("c1", "compile_project", {})),
            _reply(_call("c2", "simulate_firmware", LED_SPEC)),
            _reply(_call("c3", "apply_patch", {"path": "Core/Src/main.c", "patch": patch})),
            _reply(_call("c4", "compile_project", {}), _call("c5", "simulate_firmware", LED_SPEC)),
            _reply(),
        ],
    )
    assert adapter.specs == [LED_SPEC, LED_SPEC]
    assert "HAL_Delay(500)" in (tmp_path / "Core" / "Src" / "main.c").read_text(encoding="utf-8")
    sims = [e for e in run.events if e["type"] == "validation" and "仿真" in e["title"]]
    assert [e["status"] for e in sims] == ["failed", "success"]
    assert run.status == "success"


def test_failed_simulation_fails_the_run(tmp_path: Path, monkeypatch) -> None:
    adapter = SimAdapter(tmp_path, ["FAIL"])
    run = _run(
        tmp_path,
        monkeypatch,
        adapter,
        [_reply(_call("c1", "compile_project", {})), _reply(_call("c2", "simulate_firmware", LED_SPEC)), _reply()],
    )
    assert run.status == "failed"


def test_unavailable_simulator_does_not_fail_the_run(tmp_path: Path, monkeypatch) -> None:
    adapter = SimAdapter(tmp_path, ["UNAVAILABLE"])
    run = _run(
        tmp_path,
        monkeypatch,
        adapter,
        [_reply(_call("c1", "compile_project", {})), _reply(_call("c2", "simulate_firmware", LED_SPEC)), _reply()],
    )
    assert run.status == "success"
