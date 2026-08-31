from __future__ import annotations

import shutil
import subprocess
from typing import Any

# Fixed allowlist — never interpolate user input into argv.
KNOWN_TOOLS: tuple[tuple[str, str], ...] = (
    ("arm-gcc", "arm-none-eabi-gcc"),
    ("make", "make"),
    ("clangd", "clangd"),
    ("cppcheck", "cppcheck"),
    ("openocd", "openocd"),
    ("git", "git"),
)


def _version(executable_name: str) -> str | None:
    exe = shutil.which(executable_name)
    if not exe:
        return None
    try:
        r = subprocess.run(
            [exe, "--version"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
            shell=False,
        )
        line = (r.stdout or r.stderr).splitlines()
        return line[0].strip() if line else exe
    except (OSError, subprocess.TimeoutExpired):
        return None


def tool_status() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for tid, cmd in KNOWN_TOOLS:
        ver = _version(cmd)
        out.append({"id": tid, "name": cmd, "installed": ver is not None, "version": ver})
    return out


def gcc_installed() -> bool:
    return shutil.which("arm-none-eabi-gcc") is not None


def make_installed() -> bool:
    return shutil.which("make") is not None
