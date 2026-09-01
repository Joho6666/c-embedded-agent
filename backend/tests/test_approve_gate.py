import asyncio
from pathlib import Path

import pytest

from app.agent.runtime import AgentRun, _write_with_diff, resolve_approval


@pytest.mark.asyncio
async def test_code_mode_does_not_write_until_approved(tmp_path: Path) -> None:
    (tmp_path / "Core" / "Inc").mkdir(parents=True)
    target = tmp_path / "Core" / "Inc" / "gpio.h"
    target.write_text("old\n", encoding="utf-8")
    run = AgentRun("r-approve", "p", "task", "code")
    task = asyncio.create_task(_write_with_diff(run, tmp_path, "Core/Inc/gpio.h", "new\n"))
    await asyncio.sleep(0.05)
    assert target.read_text(encoding="utf-8") == "old\n"
    resolve_approval(run, "approved")
    assert await task == "ok"
    assert target.read_text(encoding="utf-8") == "new\n"


@pytest.mark.asyncio
async def test_code_mode_reject_leaves_file(tmp_path: Path) -> None:
    (tmp_path / "Core" / "Inc").mkdir(parents=True)
    target = tmp_path / "Core" / "Inc" / "gpio.h"
    target.write_text("old\n", encoding="utf-8")
    run = AgentRun("r-reject", "p", "task", "code")
    task = asyncio.create_task(_write_with_diff(run, tmp_path, "Core/Inc/gpio.h", "new\n"))
    await asyncio.sleep(0.05)
    resolve_approval(run, "rejected")
    assert await task == "rejected"
    assert target.read_text(encoding="utf-8") == "old\n"
