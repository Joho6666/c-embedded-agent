from __future__ import annotations

import os
from pathlib import Path

_CANDIDATE_BIN_DIRS = (
    Path.home() / "tools" / "xpack-arm-none-eabi-gcc-13.3.1-1.1" / "bin",
    Path.home() / "tools" / "xpack-windows-build-tools-4.4.1-3" / "bin",
)


def extra_bin_dirs() -> list[Path]:
    env = os.environ.get("CEA_TOOLCHAIN_PATH", "")
    dirs: list[Path] = []
    for part in env.split(os.pathsep):
        p = Path(part.strip())
        if part.strip() and p.is_dir():
            dirs.append(p)
    for p in _CANDIDATE_BIN_DIRS:
        if p.is_dir():
            dirs.append(p)
    return dirs


def prepend_toolchain_path() -> None:
    extra = [str(p) for p in extra_bin_dirs()]
    if not extra:
        return
    current = os.environ.get("PATH", "")
    prefix = os.pathsep.join(extra)
    if current.startswith(prefix):
        return
    os.environ["PATH"] = prefix + os.pathsep + current
