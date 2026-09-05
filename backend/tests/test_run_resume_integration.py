from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.checkpoint import load_run_checkpoint
from app.agent.runtime import (
    AgentRun,
    CrashInjectedError,
    _patch_with_diff,
    _write_with_diff,
    restore_run_from_checkpoint,
    run_agent,
)
from app.platforms.base import PlatformResult


@pytest.mark.asyncio
async def test_crash_after_plan_and_resume_preserves_plan(tmp_path: Path) -> None:
    # Setup project structure in tmp_path with project.json for platform detection
    (tmp_path / "Core" / "Src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "Core" / "Inc").mkdir(parents=True, exist_ok=True)
    (tmp_path / "Makefile").write_text("all:\n", encoding="utf-8")
    (tmp_path / "Core" / "Src" / "main.c").write_text("/* main */\n", encoding="utf-8")
    (tmp_path / "project.json").write_text(
        json.dumps({"adapterId": "stm32f103-hal", "mcu": "STM32F103C8T6", "framework": "HAL"}),
        encoding="utf-8",
    )

    with patch("app.agent.runtime.project_root", return_value=tmp_path):
        run = AgentRun("run-crash-plan-1", "test-p1", "Blink PC13 LED", "auto")
        run.crash_at_phase = "after_plan"

        with pytest.raises(CrashInjectedError, match="after_plan"):
            await run_agent(run)

        # Verify checkpoint saved on crash
        cp = load_run_checkpoint("run-crash-plan-1")
        assert cp is not None
        assert cp.phase == "after_plan" or cp.phase == "plan"
        assert "plan" in cp.completed_steps
        assert cp.action_plan is not None
        saved_plan = cp.action_plan

        # Resume the run
        resumed_run = restore_run_from_checkpoint(cp)
        assert resumed_run.resumed is True
        assert resumed_run.action_plan == saved_plan
        assert "plan" in resumed_run.completed_steps


@pytest.mark.asyncio
async def test_crash_after_patch_does_not_duplicate_patch(tmp_path: Path) -> None:
    # Setup project structure in tmp_path
    (tmp_path / "Core" / "Src").mkdir(parents=True, exist_ok=True)
    main_c = tmp_path / "Core" / "Src" / "main.c"
    main_c.write_text("/* USER CODE BEGIN Header */\n/* header */\n", encoding="utf-8")

    # Construct a valid unified diff
    patch_text = (
        "--- Core/Src/main.c\n"
        "+++ Core/Src/main.c\n"
        "@@ -1,2 +1,3 @@\n"
        "+/* CEA_PATCH_TEST_MARKER */\n"
        " /* USER CODE BEGIN Header */\n"
        " /* header */\n"
    )

    run = AgentRun("run-crash-patch-1", "test-p2", "Patch main.c", "auto")
    run.crash_at_phase = "after_patch"

    with pytest.raises(CrashInjectedError, match="after_patch"):
        await _patch_with_diff(run, tmp_path, "Core/Src/main.c", patch_text)

    # Verify patch was applied to disk before crash
    patched_content = main_c.read_text(encoding="utf-8")
    assert "CEA_PATCH_TEST_MARKER" in patched_content

    # Verify checkpoint saved
    cp = load_run_checkpoint("run-crash-patch-1")
    assert cp is not None
    assert cp.phase == "after_patch"
    assert "patch:Core/Src/main.c" in cp.completed_steps
    assert len(cp.executed_tools) == 1
    assert cp.executed_tools[0]["tool"] == "apply_patch"

    # Resume run and simulate executing the same patch again
    resumed = restore_run_from_checkpoint(cp)
    result = await _patch_with_diff(resumed, tmp_path, "Core/Src/main.c", patch_text)

    # Must NOT fail with reject or re-apply patch twice
    assert "already applied" in result.lower()
    final_content = main_c.read_text(encoding="utf-8")
    # Verify marker is present exactly once
    assert final_content.count("CEA_PATCH_TEST_MARKER") == 1


@pytest.mark.asyncio
async def test_crash_during_compile_and_resume_retries_idempotently(tmp_path: Path) -> None:
    run = AgentRun("run-crash-compile-1", "test-p3", "Compile test", "auto")
    run.crash_at_phase = "during_compile"

    build_res = PlatformResult(
        status="PASS",
        operation="build",
        adapter_id="stm32f103-hal",
        reason="Built successfully",
        data={"combined": "Built successfully", "artifacts": [{"name": "firmware.elf"}]},
    )

    mock_adapter = MagicMock()
    mock_adapter.build_streaming = AsyncMock(return_value=build_res)
    mock_adapter.adapter_id = "stm32f103-hal"
    mock_adapter.validate_static.return_value = PlatformResult(status="PASS", operation="validate", adapter_id="stm32f103-hal")

    from app.agent.runtime import _compile

    with pytest.raises(CrashInjectedError, match="during_compile"):
        await _compile(run, tmp_path, mock_adapter)

    cp = load_run_checkpoint("run-crash-compile-1")
    assert cp is not None
    assert cp.phase == "during_compile"

    # Resume and compile without crash
    resumed = restore_run_from_checkpoint(cp)
    resumed.crash_at_phase = None
    res = await _compile(resumed, tmp_path, mock_adapter)
    assert res.get("success") is True
    assert resumed.phase == "after_compile"


@pytest.mark.asyncio
async def test_crash_flash_and_dangerous_tool_replay_protection(tmp_path: Path) -> None:
    run = AgentRun("run-crash-flash-1", "test-p4", "Flash test", "auto")
    run.crash_at_phase = "before_flash"

    flash_res = PlatformResult(
        status="PASS",
        operation="flash",
        adapter_id="stm32f103-hal",
        data={"output": "Flash verified"},
    )
    mock_adapter = MagicMock()
    mock_adapter.flash.return_value = flash_res

    from app.agent.runtime import _flash_tool

    with pytest.raises(CrashInjectedError, match="before_flash"):
        await _flash_tool(run, tmp_path, mock_adapter)

    cp = load_run_checkpoint("run-crash-flash-1")
    assert cp is not None
    assert cp.phase == "before_flash"

    # Resumed run: dangerous tool verifies before retry
    resumed = restore_run_from_checkpoint(cp)
    resumed.crash_at_phase = None
    flash_out = await _flash_tool(resumed, tmp_path, mock_adapter)
    assert "Flash verified" in flash_out
    assert resumed.phase == "after_flash"
    assert "flash" in resumed.completed_steps


@pytest.mark.asyncio
async def test_resume_preserves_messages_iteration_and_tool_results() -> None:
    run = AgentRun("run-crash-hist-1", "test-p5", "History check", "auto")
    run.iteration = 3
    run.messages = [
        {"role": "user", "content": "initial prompt"},
        {"role": "assistant", "content": "thought step 1"},
        {"role": "tool", "content": "tool output 1"},
    ]
    run.last_tool_call = {"name": "read_file", "arguments": {"path": "main.c"}}
    run.last_tool_result = {"name": "read_file", "result": "int main() {}"}
    run.completed_steps = ["plan", "step-1"]
    run.phase = "tool_call"
    run.save_checkpoint()

    cp = load_run_checkpoint("run-crash-hist-1")
    assert cp is not None
    resumed = restore_run_from_checkpoint(cp)

    assert resumed.iteration == 3
    assert len(resumed.messages) == 3
    assert resumed.last_tool_call == {"name": "read_file", "arguments": {"path": "main.c"}}
    assert resumed.last_tool_result == {"name": "read_file", "result": "int main() {}"}
    assert resumed.completed_steps == ["plan", "step-1"]
    assert resumed.resumed is True
