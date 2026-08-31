from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.config.settings import settings
from app.tools.gcc_parser import parse_gcc_output


class CompileError(RuntimeError):
    pass


def compile_project(project_root: Path) -> dict[str, Any]:
    make = shutil.which("make")
    gcc = shutil.which("arm-none-eabi-gcc")
    if not gcc:
        raise CompileError("未检测到 arm-none-eabi-gcc，无法真实编译。")
    if not make:
        raise CompileError("未检测到 make，无法真实编译。")

    root = project_root.resolve()
    proc = subprocess.run(
        [make, "-j4"],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=settings.compile_timeout_sec,
        check=False,
        shell=False,
    )
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if len(combined.encode()) > settings.max_stdout_bytes:
        combined = combined[: settings.max_stdout_bytes]
    diagnostics = parse_gcc_output(combined)
    artifacts = []
    for name in ("firmware.elf", "firmware.hex", "firmware.bin", "firmware.map"):
        p = root / name
        if p.is_file():
            artifacts.append({"name": name, "path": name, "size": p.stat().st_size})
    size = _size(root) if (root / "firmware.elf").is_file() else None
    return {
        "success": proc.returncode == 0,
        "exit_code": proc.returncode,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
        "combined": combined,
        "diagnostics": diagnostics,
        "artifacts": artifacts,
        "memory": size,
    }


def _size(project_root: Path) -> dict[str, int] | None:
    exe = shutil.which("arm-none-eabi-size")
    if not exe:
        return None
    r = subprocess.run(
        [exe, "firmware.elf"],
        cwd=str(project_root.resolve()),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        shell=False,
    )
    lines = [ln for ln in (r.stdout or "").splitlines() if ln.strip()]
    if len(lines) < 2:
        return None
    parts = lines[-1].split()
    if len(parts) < 3:
        return None
    text, data, bss = int(parts[0]), int(parts[1]), int(parts[2])
    return {"text": text, "data": data, "bss": bss, "flash": text + data, "ram": data + bss}
