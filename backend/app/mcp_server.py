"""C-Embedded MCP server: build, one-click flash and live board state for any agent harness.

Run (stdio):  python scripts/cea_mcp.py      (or: python -m app.mcp_server from backend/)

Tools are thin wrappers over ``DeviceService``; the session (virtual board or real
probe, serial history, last build/flash) lives as long as the harness keeps this
server process running.
"""

from __future__ import annotations

import atexit
import os
import shutil
import sys
import threading
from pathlib import Path
from typing import Any

import anyio
from mcp.server.fastmcp import FastMCP

from app.device.base import DeviceError
from app.device.service import DeviceService, resolve_project

INSTRUCTIONS = """C-Embedded tools for STM32 firmware projects (Makefile + arm-none-eabi-gcc).
Workflow: edit code -> `flash` with an `expect` string the firmware should print -> read `status`.
Use `verify_behavior` to assert timing (LED blink periods) and UART output deterministically.
Every result carries `evidence`: SIMULATED (virtual Blue Pill on Renode) or HARDWARE (real probe).
Never tell the user firmware works unless a tool result shows it; say which evidence kind it was.
`project` defaults to CEA_PROJECT or the current directory."""

mcp = FastMCP("cea-embedded", instructions=INSTRUCTIONS)
_service: DeviceService | None = None
_service_lock = threading.Lock()


def service() -> DeviceService:
    global _service
    with _service_lock:
        if _service is None:
            _service = DeviceService()
            atexit.register(_service.close)
        return _service


async def _run(fn, *args: Any, **kwargs: Any) -> dict[str, Any]:
    try:
        return await anyio.to_thread.run_sync(lambda: fn(*args, **kwargs))
    except DeviceError as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def doctor() -> dict[str, Any]:
    """Check the local toolchain, simulator and probe setup and which device backend is active."""

    def check() -> dict[str, Any]:
        from app.sim.renode import find_renode, find_test_python
        from app.tools.toolchain import prepend_toolchain_path

        prepend_toolchain_path()
        svc = service()
        ok, reason = svc.backend.available()
        try:
            from app.tools.serialutil import list_ports

            ports = [p.get("device") for p in list_ports()]
        except Exception:  # noqa: BLE001
            ports = []
        renode = find_renode()
        return {
            "arm_gcc": shutil.which("arm-none-eabi-gcc"),
            "make": shutil.which("make"),
            "renode": str(renode) if renode else None,
            "behaviour_checks_python": find_test_python(),
            "openocd": shutil.which("openocd"),
            "serial_ports": ports,
            "backend": svc.backend.info(),
            "backend_available": ok,
            "backend_reason": reason,
        }

    return await _run(check)


@mcp.tool()
async def build(project: str | None = None) -> dict[str, Any]:
    """Compile the firmware project with make. Returns errors (file/line/message), warnings count and flash/RAM usage."""
    return await _run(service().build, project)


@mcp.tool()
async def flash(project: str | None = None, expect: str | None = None, observe_seconds: float = 2.0) -> dict[str, Any]:
    """One-click: build -> flash to the board -> run -> capture serial for `observe_seconds`.

    Pass `expect` (text the firmware should print) to get a pass/fail on it. The board keeps
    running afterwards; use `status` / `serial_read` to watch it.
    """
    return await _run(service().flash, project, expect=expect, observe_s=max(0.2, min(observe_seconds, 30.0)))


@mcp.tool()
async def status(pins: list[str] | None = None) -> dict[str, Any]:
    """Latest board state: backend and evidence kind, firmware on the board, last build/flash, recent serial, pin levels."""
    return await _run(service().status, pins)


@mcp.tool()
async def serial_read(limit: int = 50, since_seq: int = 0) -> dict[str, Any]:
    """Serial lines printed by the current firmware (pass `since_seq` from a previous call to get only new lines)."""
    return await _run(service().serial_tail, max(1, min(limit, 500)), since_seq)


@mcp.tool()
async def serial_write(text: str, channel: str = "usart1") -> dict[str, Any]:
    """Send text to the board's UART (e.g. a command for the firmware's console). Include '\\r\\n' if needed."""
    return await _run(service().write_serial, text, channel)


@mcp.tool()
async def read_pins(pins: list[str]) -> dict[str, Any]:
    """Read GPIO output/input levels right now, e.g. ["PC13", "PA0"]."""
    return await _run(service().read_pins, pins)


@mcp.tool()
async def verify_behavior(
    project: str | None = None,
    led: list[dict[str, Any]] | None = None,
    uart: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Deterministic behaviour test in a fresh simulated board (independent of the live session).

    led:  [{"pin": "PC13", "on_ms": 500, "off_ms": 500}]   (Blue Pill LED is active-low; on = pin low)
    uart: [{"peripheral": "usart1", "expect": "CEA:BOOT OK"}]
    """

    def run() -> dict[str, Any]:
        from app.sim.renode import checks_from_spec, simulate

        built = service().build(project)
        if not built.get("success"):
            return {"success": False, "stage": "build", "build": built}
        checks = checks_from_spec({"led": led or [], "uart": uart or []})
        root = resolve_project(project)
        return simulate(root / "firmware.elf", checks).to_dict()

    return await _run(run)


@mcp.tool()
async def pin_check(project: str | None = None) -> dict[str, Any]:
    """List which peripherals/GPIO use each pin in the project and flag pins claimed twice."""

    def run() -> dict[str, Any]:
        from app.tools.periph_gen import pin_occupancy

        occupied = pin_occupancy(resolve_project(project))
        conflicts = {pin: owners for pin, owners in occupied.items() if len(owners) > 1}
        return {"pins": occupied, "conflicts": conflicts}

    return await _run(run)


def main() -> None:
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    mcp.run("stdio")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    main()
