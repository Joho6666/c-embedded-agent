from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

ALLOWED_INTERFACE = "interface/stlink.cfg"
ALLOWED_TARGET = "target/stm32f1x.cfg"


class FlashError(RuntimeError):
    pass


def detect_chip_id() -> dict[str, Any]:
    exe = shutil.which("openocd")
    if not exe:
        return {"available": False, "id": None, "family": None}
    r = subprocess.run(
        [
            exe,
            "-f",
            ALLOWED_INTERFACE,
            "-f",
            ALLOWED_TARGET,
            "-c",
            "init; mdw 0xE0042000 1; shutdown",
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
        shell=False,
    )
    text = (r.stdout or "") + "\n" + (r.stderr or "")
    family = None
    if "stm32f1" in text.lower() or "0x1ba01477" in text.lower():
        family = "STM32F1"
    elif "stm32f4" in text.lower():
        family = "STM32F4"
    return {"available": True, "output": text[-2000:], "family": family}


def flash_elf(project_root: Path) -> dict[str, Any]:
    exe = shutil.which("openocd")
    if not exe:
        raise FlashError("未检测到 openocd")
    elf = project_root / "firmware.elf"
    if not elf.is_file():
        raise FlashError("缺少 firmware.elf")
    chip = detect_chip_id()
    if chip.get("family") and chip["family"] != "STM32F1":
        raise FlashError(f"MCU 不匹配：项目 STM32F103，真机 {chip['family']}")
    r = subprocess.run(
        [
            exe,
            "-f",
            ALLOWED_INTERFACE,
            "-f",
            ALLOWED_TARGET,
            "-c",
            f"program {elf.as_posix()} verify reset exit",
        ],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        shell=False,
    )
    combined = (r.stdout or "") + "\n" + (r.stderr or "")
    return {"success": r.returncode == 0, "exit_code": r.returncode, "output": combined[-8000:], "chip": chip}
