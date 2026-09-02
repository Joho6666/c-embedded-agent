"""Read-only Cortex-M fault dump and ELF symbol lookup. No user strings in argv."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.tools.flash import ALLOWED_INTERFACE, ALLOWED_TARGET, detect_chip_id
from app.workspace.paths import resolve_in_root

_SYM = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_HEX = re.compile(r"0x[0-9a-fA-F]{8}")
_ALLOWED_REGS = frozenset({"CFSR", "HFSR", "MMFAR", "BFAR", "DBGMCU"})


def dump_fault() -> dict[str, Any]:
    probe = detect_chip_id()
    if not probe.get("available"):
        return {"available": False, "status": "UNAVAILABLE", "reason": "Hardware Not Tested", "regs": {}}
    exe = shutil.which("openocd")
    if not exe:
        return {"available": False, "status": "UNAVAILABLE", "reason": "openocd missing", "regs": {}}
    r = subprocess.run(
        [
            exe,
            "-f",
            ALLOWED_INTERFACE,
            "-f",
            ALLOWED_TARGET,
            "-c",
            "init; halt; mdw 0xE000ED28 1; mdw 0xE000ED2C 1; mdw 0xE000ED34 1; mdw 0xE000ED38 1; shutdown",
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
        shell=False,
    )
    text = (r.stdout or "") + "\n" + (r.stderr or "")
    words = _HEX.findall(text)
    names = ("CFSR", "HFSR", "MMFAR", "BFAR")
    regs = {n: words[i] for i, n in enumerate(names) if i < len(words)}
    return {
        "available": True,
        "status": "UNKNOWN",
        "regs": regs,
        "reason": "halt dump only — not a PASS",
        "output": text[-1200:],
    }


def read_register(name: str) -> dict[str, Any]:
    key = str(name or "").strip().upper()
    aliases = {
        "0XE000ED28": "CFSR",
        "0XE000ED2C": "HFSR",
        "0XE000ED34": "MMFAR",
        "0XE000ED38": "BFAR",
        "0XE0042000": "DBGMCU",
    }
    key = aliases.get(key, key)
    if key not in _ALLOWED_REGS:
        return {
            "available": False,
            "status": "UNAVAILABLE",
            "reason": "register not in allowlist (CFSR/HFSR/MMFAR/BFAR/DBGMCU)",
            "value": None,
        }
    if key == "DBGMCU":
        probe = detect_chip_id()
        words = _HEX.findall(probe.get("output") or "")
        value = words[-1] if words else None
        return {
            "available": bool(probe.get("available")),
            "status": "UNKNOWN" if value else "UNAVAILABLE",
            "name": key,
            "value": value,
            "reason": "read only — not a PASS",
        }
    dumped = dump_fault()
    if not dumped.get("available"):
        return {
            "available": False,
            "status": "UNAVAILABLE",
            "reason": dumped.get("reason"),
            "value": None,
            "name": key,
        }
    value = (dumped.get("regs") or {}).get(key)
    return {
        "available": True,
        "status": "UNKNOWN" if value else "UNAVAILABLE",
        "name": key,
        "value": value,
        "reason": "read only — not a PASS",
    }


def read_symbol(root: Path, name: str) -> dict[str, Any]:
    if not _SYM.fullmatch(str(name or "")):
        return {"available": False, "status": "UNAVAILABLE", "reason": "invalid symbol"}
    try:
        elf = resolve_in_root(root, "firmware.elf")
    except Exception:
        return {"available": False, "status": "UNAVAILABLE", "reason": "path rejected"}
    if not elf.is_file():
        return {"available": False, "status": "UNAVAILABLE", "reason": "firmware.elf missing"}
    nm = shutil.which("arm-none-eabi-nm")
    if not nm:
        from app.tools.toolchain import prepend_toolchain_path

        prepend_toolchain_path()
        nm = shutil.which("arm-none-eabi-nm")
    if not nm:
        return {"available": False, "status": "UNAVAILABLE", "reason": "arm-none-eabi-nm missing"}
    r = subprocess.run(
        [nm, "firmware.elf"],
        cwd=str(elf.parent),
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        shell=False,
    )
    addr = None
    for line in (r.stdout or "").splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[-1] == name:
            addr = "0x" + parts[0]
            break
    if not addr:
        return {"available": True, "status": "UNAVAILABLE", "reason": "symbol not found", "name": name}
    return {
        "available": True,
        "status": "UNKNOWN",
        "name": name,
        "addr": addr,
        "value": None,
        "reason": "ELF symbol address only; live mdw not used for arbitrary addresses",
    }
