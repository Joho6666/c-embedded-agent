import asyncio
from pathlib import Path

from app.agent.runtime import AgentRun, _write_with_diff, request_stop, resolve_approval, RUNS


def test_code_mode_does_not_write_until_approved(tmp_path: Path) -> None:
    async def _run() -> None:
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

    asyncio.run(_run())


def test_code_mode_reject_leaves_file(tmp_path: Path) -> None:
    async def _run() -> None:
        (tmp_path / "Core" / "Inc").mkdir(parents=True)
        target = tmp_path / "Core" / "Inc" / "gpio.h"
        target.write_text("old\n", encoding="utf-8")
        run = AgentRun("r-reject", "p", "task", "code")
        task = asyncio.create_task(_write_with_diff(run, tmp_path, "Core/Inc/gpio.h", "new\n"))
        await asyncio.sleep(0.05)
        resolve_approval(run, "rejected")
        assert await task == "rejected"
        assert target.read_text(encoding="utf-8") == "old\n"

    asyncio.run(_run())


def test_stop_while_waiting_does_not_write(tmp_path: Path) -> None:
    async def _run() -> None:
        (tmp_path / "Core" / "Inc").mkdir(parents=True)
        target = tmp_path / "Core" / "Inc" / "gpio.h"
        target.write_text("old\n", encoding="utf-8")
        run = AgentRun("r-stop-wait", "p", "task", "code")
        RUNS[run.id] = run
        task = asyncio.create_task(_write_with_diff(run, tmp_path, "Core/Inc/gpio.h", "new\n"))
        await asyncio.sleep(0.05)
        await request_stop(run)
        out = await task
        assert out in {"rejected", "RUN_STOPPED"}
        assert target.read_text(encoding="utf-8") == "old\n"

    asyncio.run(_run())


def test_approve_once(tmp_path: Path) -> None:
    async def _run() -> None:
        (tmp_path / "Core" / "Inc").mkdir(parents=True)
        target = tmp_path / "Core" / "Inc" / "gpio.h"
        target.write_text("old\n", encoding="utf-8")
        run = AgentRun("r-once", "p", "task", "code")
        task = asyncio.create_task(_write_with_diff(run, tmp_path, "Core/Inc/gpio.h", "once\n"))
        await asyncio.sleep(0.05)
        resolve_approval(run, "once")
        assert await task == "ok"
        assert target.read_text(encoding="utf-8") == "once\n"
        assert run.always_approve is False

    asyncio.run(_run())


def test_always_approve_skips_later_waits(tmp_path: Path) -> None:
    async def _run() -> None:
        (tmp_path / "Core" / "Inc").mkdir(parents=True)
        target = tmp_path / "Core" / "Inc" / "gpio.h"
        target.write_text("old\n", encoding="utf-8")
        run = AgentRun("r-always", "p", "task", "code")
        t1 = asyncio.create_task(_write_with_diff(run, tmp_path, "Core/Inc/gpio.h", "a\n"))
        await asyncio.sleep(0.05)
        resolve_approval(run, "always")
        assert await t1 == "ok"
        assert run.always_approve is True
        t2 = asyncio.create_task(_write_with_diff(run, tmp_path, "Core/Inc/gpio.h", "b\n"))
        assert await t2 == "ok"
        assert target.read_text(encoding="utf-8") == "b\n"

    asyncio.run(_run())
