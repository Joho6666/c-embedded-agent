from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.security import FlashRateLimitError, check_flash_budget, note_flash
from app.core.types import FAIL, HARDWARE_ACTION, SUCCESS, UNAVAILABLE, envelope
from app.tools.flash import FlashError, detect_chip_id, flash_elf


def flash_firmware_at(root: Path) -> dict[str, Any]:
    try:
        check_flash_budget()
    except FlashRateLimitError as e:
        return envelope(
            status=FAIL,
            side_effect=HARDWARE_ACTION,
            success=False,
            available=False,
            reason=str(e),
            exit_code=None,
            stdout="",
            stderr=str(e),
        )
    elf = root / "firmware.elf"
    if not elf.is_file():
        return envelope(
            status=FAIL,
            side_effect=HARDWARE_ACTION,
            success=False,
            available=False,
            reason="firmware.elf is missing — build before flash",
            exit_code=None,
            stdout="",
            stderr="缺少 firmware.elf",
        )
    note_flash()
    try:
        result = flash_elf(root)
    except FlashError as e:
        msg = str(e)
        unavailable = "未检测到 openocd" in msg or "openocd" in msg.lower()
        return envelope(
            status=UNAVAILABLE if unavailable else FAIL,
            side_effect=HARDWARE_ACTION,
            success=False,
            available=not unavailable,
            reason=msg,
            exit_code=None,
            stdout="",
            stderr=msg,
            chip=detect_chip_id(),
        )
    ok = bool(result.get("success"))
    return envelope(
        status=SUCCESS if ok else FAIL,
        side_effect=HARDWARE_ACTION,
        success=ok,
        available=True,
        reason=None if ok else "openocd flash failed",
        exit_code=result.get("exit_code"),
        stdout="",
        stderr=result.get("output") or "",
        output=result.get("output") or "",
        chip=result.get("chip"),
        elf=str(elf),
    )
