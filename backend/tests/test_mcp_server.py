"""End-to-end over the real MCP stdio transport, the way a harness launches the plugin."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import anyio
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from tests.test_sim_renode import _renode_ready

REPO = Path(__file__).resolve().parents[2]
LAUNCHER = REPO / "scripts" / "cea_mcp.py"
EXPECTED_TOOLS = {"doctor", "build", "flash", "status", "serial_read", "serial_write", "read_pins", "verify_behavior", "pin_check"}


def _params(env: dict[str, str] | None = None) -> StdioServerParameters:
    return StdioServerParameters(command=sys.executable, args=[str(LAUNCHER)], env={**os.environ, "CEA_DEVICE": "virtual", **(env or {})})


def _payload(result) -> dict:
    assert not result.isError, result.content
    return json.loads(result.content[0].text)


async def _session(env: dict[str, str] | None, body) -> None:
    async with stdio_client(_params(env)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await body(session)


def test_tools_are_listed_and_doctor_reports_environment() -> None:
    async def body(session: ClientSession) -> None:
        tools = {tool.name for tool in (await session.list_tools()).tools}
        assert EXPECTED_TOOLS <= tools
        doctor = _payload(await session.call_tool("doctor", {}))
        assert doctor["backend"]["kind"] == "virtual"
        assert {"arm_gcc", "renode", "openocd", "backend_available"} <= doctor.keys()
        state = _payload(await session.call_tool("status", {}))
        assert state["last_flash"] is None and state["device"]["evidence"] == "SIMULATED"

    anyio.run(_session, None, body)


def test_flash_rejects_non_project(tmp_path: Path) -> None:
    async def body(session: ClientSession) -> None:
        result = _payload(await session.call_tool("flash", {"project": str(tmp_path)}))
        assert result["success"] is False and "Makefile" in result["error"]

    anyio.run(_session, None, body)


@pytest.mark.skipif(not _renode_ready(), reason="Renode + ARM GCC not available")
def test_one_click_flash_and_live_state_on_virtual_board(tmp_path: Path) -> None:
    project = shutil.copytree(
        REPO / "examples" / "golden" / "stm32f103_usart",
        tmp_path / "usart",
        ignore=shutil.ignore_patterns("*.o", "*.d", "*.elf", "*.hex", "*.bin", "*.map"),
    )

    async def body(session: ClientSession) -> None:
        flashed = _payload(await session.call_tool("flash", {"project": str(project), "expect": "Hello", "observe_seconds": 1.2}))
        assert flashed["success"] and flashed["expect_found"] is True
        assert flashed["evidence"] == "SIMULATED"
        assert "" not in flashed["serial"]
        state = _payload(await session.call_tool("status", {"pins": ["PC13"]}))
        assert state["last_flash"]["success"] and state["project"] == str(project)
        assert "board_led_on" in state["pins"]["PC13"]
        lines = _payload(await session.call_tool("serial_read", {"limit": 5}))
        assert lines["lines"] and all(line["text"] == "Hello" for line in lines["lines"])
        pins = _payload(await session.call_tool("pin_check", {"project": str(project)}))
        assert "PA9" in pins["pins"]

    anyio.run(_session, None, body)
