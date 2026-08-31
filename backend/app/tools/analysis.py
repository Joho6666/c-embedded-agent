from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def generate_compile_commands(root: Path) -> Path | None:
    makefile = root / "Makefile"
    if not makefile.is_file():
        return None
    entries = []
    include = [
        "-ICore/Inc",
        "-IDrivers/CMSIS/Include",
        "-IDrivers/CMSIS/Device/ST/STM32F1xx/Include",
        "-IDrivers/STM32F1xx_HAL_Driver/Inc",
        "-DSTM32F103xB",
        "-DUSE_HAL_DRIVER",
    ]
    for p in (root / "Core" / "Src").glob("*.c") if (root / "Core" / "Src").is_dir() else []:
        rel = str(p.relative_to(root)).replace("\\", "/")
        entries.append(
            {
                "directory": str(root),
                "file": rel,
                "command": "arm-none-eabi-gcc -mcpu=cortex-m3 -mthumb "
                + " ".join(include)
                + f" -c {rel}",
            }
        )
    out = root / "compile_commands.json"
    out.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    return out


def clangd_diagnostics(root: Path) -> dict[str, Any]:
    exe = shutil.which("clangd")
    if not exe:
        return {"available": False, "diagnostics": []}
    generate_compile_commands(root)
    diags: list[dict[str, Any]] = []
    src = root / "Core" / "Src"
    files = list(src.glob("*.c")) if src.is_dir() else []
    for f in files[:6]:
        r = subprocess.run(
            [exe, "--check=" + str(f), "--compile-commands-dir=" + str(root)],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
            shell=False,
        )
        text = (r.stderr or "") + "\n" + (r.stdout or "")
        for line in text.splitlines():
            if "error:" in line or "warning:" in line:
                diags.append({"file": str(f.name), "message": line.strip(), "source": "clangd"})
    return {"available": True, "diagnostics": diags}


def cppcheck_project(root: Path) -> dict[str, Any]:
    exe = shutil.which("cppcheck")
    if not exe:
        return {"available": False, "diagnostics": []}
    r = subprocess.run(
        [
            exe,
            "--enable=warning,style,performance,portability",
            "--error-exitcode=0",
            "-q",
            "Core",
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=40,
        check=False,
        shell=False,
    )
    diags = []
    for line in ((r.stderr or "") + "\n" + (r.stdout or "")).splitlines():
        if not line.strip():
            continue
        diags.append({"message": line.strip(), "source": "cppcheck", "severity": "warning"})
    return {"available": True, "diagnostics": diags}
