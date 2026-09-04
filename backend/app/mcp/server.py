from __future__ import annotations

import json
from typing import Any

from app.core import (
    build_project,
    check_pin_conflicts,
    configure_peripheral,
    diagnose_build,
    flash_firmware,
    get_board_context,
    inspect_project,
    list_serial_ports,
    parse_ioc,
    read_serial,
    validate_hardware,
)

TOOL_META: list[dict[str, str]] = [
    {"name": "inspect_project", "side_effect": "READ_ONLY"},
    {"name": "parse_ioc", "side_effect": "READ_ONLY"},
    {"name": "check_pin_conflicts", "side_effect": "READ_ONLY"},
    {"name": "get_board_context", "side_effect": "READ_ONLY"},
    {"name": "build_project", "side_effect": "MUTATING"},
    {"name": "diagnose_build", "side_effect": "READ_ONLY"},
    {"name": "flash_firmware", "side_effect": "HARDWARE_ACTION"},
    {"name": "list_serial_ports", "side_effect": "READ_ONLY"},
    {"name": "read_serial", "side_effect": "READ_ONLY"},
    {"name": "validate_hardware", "side_effect": "HARDWARE_ACTION"},
    {"name": "configure_peripheral", "side_effect": "MUTATING"},
]


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _safe(fn, side_effect: str, **kwargs: Any) -> str:
    try:
        result = fn(**kwargs)
    except Exception as e:  # noqa: BLE001 — MCP must never disguise exceptions as PASS
        result = {
            "status": "FAIL",
            "side_effect": side_effect,
            "success": False,
            "available": False,
            "reason": str(e),
            "error_type": type(e).__name__,
        }
    if not isinstance(result, dict):
        result = {"status": "FAIL", "side_effect": side_effect, "reason": "core returned non-object"}
    status = str(result.get("status") or "").upper()
    if status in {"PASS", "SUCCESS"} and result.get("fabricated"):
        result["status"] = "FAIL"
        result["reason"] = "refusing fabricated evidence"
    return _json(result)


def create_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("Python package 'mcp' is required to run CEA MCP Server") from e

    mcp = FastMCP(
        "c-embedded-agent",
        instructions=(
            "C-Embedded Agent MCP v0.1 — Embedded Engineering Runtime. "
            "Call CEA Core for inspect/build/flash/serial/validate. "
            "Never treat compile success as hardware PASS. "
            "STM32F103 is the only production-supported MCU."
        ),
    )

    @mcp.tool(name="inspect_project")
    def tool_inspect_project(project_root: str) -> str:
        """READ_ONLY. Scan an embedded project: platform, MCU, board, IOC, toolchain, build system."""
        return _safe(inspect_project, "READ_ONLY", project_root=project_root)

    @mcp.tool(name="parse_ioc")
    def tool_parse_ioc(project_root: str, ioc_path: str | None = None) -> str:
        """READ_ONLY. Parse STM32CubeMX .ioc. Missing fields are null. Never invent peripherals."""
        return _safe(parse_ioc, "READ_ONLY", project_root=project_root, ioc_path=ioc_path)

    @mcp.tool(name="check_pin_conflicts")
    def tool_check_pin_conflicts(project_root: str) -> str:
        """READ_ONLY. GPIO / AF / duplicate / board-reserved pin conflicts. Result PASS/WARNING/FAIL/UNKNOWN."""
        return _safe(check_pin_conflicts, "READ_ONLY", project_root=project_root)

    @mcp.tool(name="get_board_context")
    def tool_get_board_context(project_root: str) -> str:
        """READ_ONLY. MCU/board/pins with source priority IOC > project.json > Board Profile > Default."""
        return _safe(get_board_context, "READ_ONLY", project_root=project_root)

    @mcp.tool(name="build_project")
    def tool_build_project(project_root: str) -> str:
        """MUTATING (artifacts only). Real ARM GCC / make. Missing toolchain returns UNAVAILABLE. Never fake success."""
        return _safe(build_project, "MUTATING", project_root=project_root)

    @mcp.tool(name="diagnose_build")
    def tool_diagnose_build(project_root: str, log: str | None = None) -> str:
        """READ_ONLY. Deterministic gcc/ld + Error Memory diagnosis. Pass build log. Does not compile."""
        return _safe(diagnose_build, "READ_ONLY", project_root=project_root, log=log)

    @mcp.tool(name="flash_firmware")
    def tool_flash_firmware(project_root: str, confirm: bool = False) -> str:
        """HARDWARE_ACTION. OpenOCD ST-Link flash. Requires confirm=true. Never mock PASS. Process flash budget applies."""
        if not confirm:
            return _json(
                {
                    "status": "FAIL",
                    "side_effect": "HARDWARE_ACTION",
                    "success": False,
                    "reason": "flash_firmware requires confirm=true",
                }
            )
        return _safe(flash_firmware, "HARDWARE_ACTION", project_root=project_root)

    @mcp.tool(name="list_serial_ports")
    def tool_list_serial_ports() -> str:
        """READ_ONLY. List host serial ports. Empty + UNAVAILABLE if pyserial is missing."""
        return _safe(list_serial_ports, "READ_ONLY")

    @mcp.tool(name="read_serial")
    def tool_read_serial(
        port: str,
        baud: int = 115200,
        timeout: float = 8.0,
        max_lines: int = 80,
        expect: str | None = None,
    ) -> str:
        """READ_ONLY. Read real serial output. Never fabricates logs."""
        return _safe(
            read_serial,
            "READ_ONLY",
            port=port,
            baud=baud,
            timeout=timeout,
            max_lines=max_lines,
            expect=expect,
        )

    @mcp.tool(name="validate_hardware")
    def tool_validate_hardware(
        project_root: str,
        serial_device: str | None = None,
        baud: int = 115200,
        expect: str | None = None,
        task: str = "",
        confirm: bool = False,
    ) -> str:
        """HARDWARE_ACTION. Real hardware validation. No board => UNAVAILABLE, never PASS. Requires confirm=true."""
        if not confirm:
            return _json(
                {
                    "status": "FAIL",
                    "side_effect": "HARDWARE_ACTION",
                    "hardware_passed": False,
                    "reason": "validate_hardware requires confirm=true",
                }
            )
        return _safe(
            validate_hardware,
            "HARDWARE_ACTION",
            project_root=project_root,
            serial_device=serial_device,
            baud=baud,
            expect=expect,
            task=task,
        )

    @mcp.tool(name="configure_peripheral")
    def tool_configure_peripheral(
        project_root: str,
        kind: str,
        force: bool = False,
        instance: str | None = None,
        channel: int | None = None,
        pin: str | None = None,
        mode: str | None = None,
    ) -> str:
        """MUTATING. STM32F103 peripheral codegen via CEA Core. Pin conflicts refuse unless force=true. Does not edit Drivers/."""
        args: dict[str, Any] = {"force": force}
        if instance:
            args["instance"] = instance
        if channel is not None:
            args["channel"] = channel
        if pin:
            args["pin"] = pin
        if mode:
            args["mode"] = mode
        return _safe(configure_peripheral, "MUTATING", project_root=project_root, kind=kind, args=args)

    return mcp


def main() -> None:
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
