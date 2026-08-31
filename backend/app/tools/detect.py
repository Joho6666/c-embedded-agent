from __future__ import annotations

import shutil
import subprocess
from typing import Any


def _run_version(exe_name: str) -> str | None:
    if shutil.which(exe_name) is None:
        return None
    try:
        r = subprocess.run(
            [exe_name, "--version"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
            shell=False,
        )
        line = (r.stdout or r.stderr).splitlines()
        return line[0].strip() if line else exe_name
    except (OSError, subprocess.TimeoutExpired):
        return None


def _probe_stlink() -> dict[str, Any]:
    if shutil.which("st-info") is None:
        return {"id": "stlink", "name": "st-info", "installed": False, "version": None}
    try:
        r = subprocess.run(
            ["st-info", "--probe"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
            shell=False,
        )
        text = (r.stdout or "") + (r.stderr or "")
        chip = "STM32F103C8 detected" if ("F103" in text.upper() or "stm32f1" in text.lower()) else None
        first = (text.splitlines()[:1] or ["ok"])[0]
        return {"id": "stlink", "name": "st-info", "installed": True, "version": chip or first}
    except (OSError, subprocess.TimeoutExpired):
        return {"id": "stlink", "name": "st-info", "installed": True, "version": "probe failed"}


def tool_status() -> list[dict[str, Any]]:
    names = (
        ("arm-gcc", "arm-none-eabi-gcc"),
        ("make", "make"),
        ("clangd", "clangd"),
        ("cppcheck", "cppcheck"),
        ("openocd", "openocd"),
        ("git", "git"),
    )
    out: list[dict[str, Any]] = []
    for tid, cmd in names:
        ver = _run_version(cmd)
        out.append({"id": tid, "name": cmd, "installed": ver is not None, "version": ver})
    out.append(_probe_stlink())
    return out


def gcc_installed() -> bool:
    return shutil.which("arm-none-eabi-gcc") is not None


def make_installed() -> bool:
    return shutil.which("make") is not None
