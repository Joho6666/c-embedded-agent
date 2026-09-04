"""CEA Core — the only real capability layer for Web, MCP, and CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.security import (
    FlashRateLimitError,
    PathEscapeError,
    ProjectRootError,
    ProtectedPathError,
    resolve_project_root,
)
from app.core.serial import list_serial_ports, read_serial
from app.core.types import FAIL, envelope

_READ = "READ_ONLY"
_MUT = "MUTATING"
_HW = "HARDWARE_ACTION"


def _root(project_root: str | Path) -> Path:
    return resolve_project_root(project_root)


def _fail(side_effect: str, err: Exception) -> dict[str, Any]:
    return envelope(status=FAIL, side_effect=side_effect, ok=False, available=False, reason=str(err), success=False)


def inspect_project(project_root: str | Path) -> dict[str, Any]:
    try:
        root = _root(project_root)
    except ProjectRootError as e:
        return _fail(_READ, e)
    from app.core.platforms import detect_adapter

    return detect_adapter(root).inspect(root)


def parse_ioc(project_root: str | Path, ioc_path: str | None = None) -> dict[str, Any]:
    try:
        root = _root(project_root)
    except ProjectRootError as e:
        return _fail(_READ, e)
    from app.core.platforms import stm32_adapter

    return stm32_adapter().parse_ioc(root, ioc_path)


def check_pin_conflicts(project_root: str | Path) -> dict[str, Any]:
    try:
        root = _root(project_root)
    except ProjectRootError as e:
        return _fail(_READ, e)
    from app.core.platforms import stm32_adapter

    return stm32_adapter().check_pin_conflicts(root)


def get_board_context(project_root: str | Path) -> dict[str, Any]:
    try:
        root = _root(project_root)
    except ProjectRootError as e:
        return _fail(_READ, e)
    from app.core.platforms import stm32_adapter

    return stm32_adapter().board_context(root)


def build_project(project_root: str | Path) -> dict[str, Any]:
    try:
        root = _root(project_root)
    except ProjectRootError as e:
        return _fail(_MUT, e)
    from app.core.platforms import stm32_adapter

    return stm32_adapter().build(root)


def diagnose_build(project_root: str | Path, log: str | None = None) -> dict[str, Any]:
    try:
        root = _root(project_root)
    except ProjectRootError as e:
        return _fail(_READ, e)
    from app.core.platforms import stm32_adapter

    return stm32_adapter().diagnose(root, log)


def flash_firmware(project_root: str | Path) -> dict[str, Any]:
    try:
        root = _root(project_root)
    except ProjectRootError as e:
        return _fail(_HW, e)
    from app.core.platforms import stm32_adapter

    return stm32_adapter().flash(root)


def validate_hardware(
    project_root: str | Path,
    *,
    serial_device: str | None = None,
    baud: int = 115200,
    expect: str | None = None,
    task: str = "",
) -> dict[str, Any]:
    try:
        root = _root(project_root)
    except ProjectRootError as e:
        return _fail(_HW, e)
    from app.core.platforms import stm32_adapter

    return stm32_adapter().validate(
        root,
        serial_device=serial_device,
        baud=baud,
        expect=expect,
        task=task,
    )


def configure_peripheral(project_root: str | Path, kind: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        root = _root(project_root)
    except ProjectRootError as e:
        return _fail(_MUT, e)
    from app.core.platforms import stm32_adapter

    return stm32_adapter().configure_peripheral(root, kind, args)


__all__ = [
    "FlashRateLimitError",
    "PathEscapeError",
    "ProjectRootError",
    "ProtectedPathError",
    "build_project",
    "check_pin_conflicts",
    "configure_peripheral",
    "diagnose_build",
    "flash_firmware",
    "get_board_context",
    "inspect_project",
    "list_serial_ports",
    "parse_ioc",
    "read_serial",
    "resolve_project_root",
    "validate_hardware",
]
