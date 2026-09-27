"""Write scope is declared per platform and shared by runtime + filesystem layers."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.agent import runtime
from app.platforms.base import PlatformResult
from app.platforms.esp32s3.adapter import Esp32S3IdfAdapter
from app.platforms.mcu8051.adapter import Mcu8051SdccAdapter
from app.platforms.stm32f103.adapter import Stm32F103Adapter
from app.tools.filesystem import write_file
from app.tools.registry import default_tool_registry
from app.workspace.paths import ProtectedPathError

REPO = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("adapter_cls", "allowed", "denied"),
    [
        (Stm32F103Adapter, ["Core/Src/main.c", "Core/Inc/app.h"], ["main.c", "Drivers/CMSIS/x.h", "main/app.c"]),
        (Esp32S3IdfAdapter, ["main/main.c", "main/app.h"], ["Core/Src/main.c", "sdkconfig", "main.c"]),
        (Mcu8051SdccAdapter, ["main.c", "uart.h", "src/timer.c"], ["8051_compat.h", "project.json", "docs/x.c"]),
    ],
)
def test_adapter_declares_standard_write_paths(adapter_cls, allowed, denied) -> None:
    adapter = adapter_cls(REPO)
    for rel in allowed:
        assert adapter.is_standard_write_path(rel), rel
    for rel in denied:
        assert not adapter.is_standard_write_path(rel), rel


def test_filesystem_write_honours_adapter_scope(tmp_path: Path) -> None:
    c51 = Mcu8051SdccAdapter(REPO).write_scope
    write_file(tmp_path, "main.c", "void main(void) {}\n", scope=c51)
    assert (tmp_path / "main.c").is_file()
    with pytest.raises(ProtectedPathError):
        write_file(tmp_path, "8051_compat.h", "", scope=c51)
    with pytest.raises(ProtectedPathError):
        write_file(tmp_path, "Makefile", "", scope=c51)

    esp = Esp32S3IdfAdapter(REPO).write_scope
    write_file(tmp_path, "main/main.c", "void app_main(void) {}\n", scope=esp)
    assert (tmp_path / "main" / "main.c").is_file()

    # Default scope (no adapter) keeps the historical STM32 behaviour.
    with pytest.raises(ProtectedPathError):
        write_file(tmp_path, "main.c", "")


@pytest.mark.parametrize("tool", ["configure_usart", "apply_error_memory_fix", "register_hal_module"])
def test_adapter_managed_writes_are_allowed_in_auto_mode(tool: str) -> None:
    registry = default_tool_registry()
    assert registry.get(tool).path_arg is None
    auto = registry.authorize(tool, "auto", standard_write_path=False, adapter_managed=True)
    assert auto.allowed and not auto.requires_approval
    code = registry.authorize(tool, "code", standard_write_path=False, adapter_managed=True)
    assert code.allowed and code.requires_approval
    assert not registry.authorize(tool, "plan", adapter_managed=True).allowed


def test_path_writes_still_need_a_standard_path_in_auto_mode() -> None:
    registry = default_tool_registry()
    assert registry.get("write_file").path_arg == "path"
    assert not registry.authorize("write_file", "auto", standard_write_path=False).allowed


class _Mcu8051ForRuntime(Mcu8051SdccAdapter):
    def __init__(self, repo_root: Path) -> None:
        super().__init__(repo_root)
        self.peripherals: list[str] = []

    def load_context(self, root: Path) -> dict:
        return {"facts": {"adapterId": self.adapter_id, "mcu": "STC89C52RC"}}

    def generate_peripheral(self, root: Path, kind: str, args: dict) -> PlatformResult:
        self.peripherals.append(kind)
        return PlatformResult("PASS", "generate", self.adapter_id, data={"files": []})


def _tool_call(call_id: str, name: str, args: dict) -> dict:
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


def test_auto_mode_runtime_executes_adapter_managed_and_flat_writes(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "main.c").write_text("void main(void) {}\n", encoding="utf-8")
    adapter = _Mcu8051ForRuntime(REPO)
    replies = iter(
        [
            {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [
                _tool_call("c1", "configure_usart", {"instance": "UART0", "baud": 9600}),
                _tool_call("c2", "write_file", {"path": "main.c", "content": "void main(void) { for (;;) {} }\n"}),
            ]}}]},
            {"choices": [{"message": {"role": "assistant", "content": "done"}}]},
        ]
    )
    seen_messages: list[list[dict]] = []

    async def fake_chat(messages, tools):
        seen_messages.append(list(messages))
        return next(replies)

    async def fake_compile(run, root, selected):
        return {"success": True}

    monkeypatch.setattr(runtime, "chat", fake_chat)
    monkeypatch.setattr(runtime, "_compile", fake_compile)
    monkeypatch.setattr(runtime, "save_model_call", lambda *a, **k: None)
    monkeypatch.setattr(runtime, "save_event", lambda *a, **k: None)
    monkeypatch.setattr(runtime, "save_file_change", lambda *a, **k: None)
    monkeypatch.setattr(runtime.AgentRun, "save_checkpoint", lambda self: None)

    run = runtime.AgentRun("scope-run", "p1", "配置串口并让主循环常驻", "auto")
    workflow = SimpleNamespace(hardware_intent=False)
    schemas = default_tool_registry().schemas()
    asyncio.run(runtime._llm_loop(run, tmp_path, adapter, workflow, schemas))

    assert adapter.peripherals == ["usart"]
    assert "for (;;)" in (tmp_path / "main.c").read_text(encoding="utf-8")
    tool_results = [m["content"] for m in seen_messages[-1] if m.get("role") == "tool"]
    assert tool_results and not any("REJECTED" in r for r in tool_results), tool_results
    assert run.status == "success"
