"""OpenOCD debug probe adapter — the first SUPPORTED DebugProbeAdapter.

Each operation spawns one OpenOCD process against the pinned ST-Link +
stm32f1x configuration (same policy as app.tools.flash). Reads are
read-only; register/memory writes are refused by the base class.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from app.hardware.probes.base import DebugProbeAdapter
from app.hardware import regmap
from app.tools.flash import ALLOWED_INTERFACE, ALLOWED_TARGET

_MDW_LINE = re.compile(r"0x[0-9A-Fa-f]{8}:\s*([0-9A-Fa-f]{8})")
_HEXWORD = re.compile(r"0x[0-9A-Fa-f]{8}")


def _env_with_toolchain() -> None:
    from app.tools.toolchain import prepend_toolchain_path

    prepend_toolchain_path()


def openocd_installed() -> bool:
    _env_with_toolchain()
    return shutil.which("openocd") is not None


class OpenOCDAdapter(DebugProbeAdapter):
    id = "openocd"
    label = "OpenOCD + ST-Link"
    adapter_status = "SUPPORTED"

    def _run(self, commands: str, timeout: int = 20) -> dict[str, Any]:
        exe = shutil.which("openocd")
        if not exe:
            _env_with_toolchain()
            exe = shutil.which("openocd")
        if not exe:
            return {"available": False, "returncode": None, "output": "", "reason": "openocd not installed"}
        import subprocess

        try:
            r = subprocess.run(
                [exe, "-f", ALLOWED_INTERFACE, "-f", ALLOWED_TARGET, "-c", f"{commands}; shutdown"],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            return {"available": True, "returncode": -1, "output": str(e), "reason": "openocd failed to run"}
        text = ((r.stdout or "") + "\n" + (r.stderr or "")).strip()
        return {"available": True, "returncode": r.returncode, "output": text[-6000:]}

    def detect(self) -> dict[str, Any]:
        installed = openocd_installed()
        probe = {"connected": False, "installed": False}
        try:
            from app.tools.detect import _probe_stlink

            probe = _probe_stlink()
        except Exception:  # noqa: BLE001 — probe metadata is best-effort
            pass
        return {
            "available": installed,
            "adapterStatus": self.adapter_status if installed else "NOT_INSTALLED",
            "toolInstalled": installed,
            "probeConnected": bool(probe.get("connected")),
            "probeInstalled": bool(probe.get("installed")),
            "status": "UNKNOWN",
            "reason": None if installed else "openocd not installed — flash/debug unavailable",
        }

    def identify_target(self) -> dict[str, Any]:
        from app.hardware.discovery import identify_target

        return identify_target()

    def flash(self, elf_path: str) -> dict[str, Any]:
        from app.tools.flash import flash_elf

        if not openocd_installed():
            return {"available": False, "status": "UNAVAILABLE", "success": False, "reason": "openocd not installed"}
        try:
            result = flash_elf(Path(elf_path).parent)
        except Exception as e:  # noqa: BLE001 — flash_elf raises FlashError / OSError
            return {"available": True, "status": "FAIL", "success": False, "reason": str(e), "output": ""}
        return {
            "available": True,
            "status": "SUCCESS" if result.get("success") else "FAIL",
            "success": bool(result.get("success")),
            "exit_code": result.get("exit_code"),
            "output": result.get("output"),
            "chip": result.get("chip"),
        }

    def reset(self, mode: str = "run") -> dict[str, Any]:
        cmd = "init; reset halt" if mode == "halt" else "init; reset run"
        r = self._run(cmd)
        if not r["available"]:
            return {"available": False, "status": "UNAVAILABLE", "reason": r["reason"], "success": False}
        ok = r["returncode"] == 0
        return {
            "available": True,
            "status": "SUCCESS" if ok else "FAIL",
            "success": ok,
            "mode": mode,
            "output": r["output"][-1500:],
        }

    def halt(self) -> dict[str, Any]:
        r = self._run("init; halt")
        if not r["available"]:
            return {"available": False, "status": "UNAVAILABLE", "reason": r["reason"]}
        ok = r["returncode"] == 0
        return {
            "available": True,
            "status": "SUCCESS" if ok else "FAIL",
            "halted": ok,
            "note": "halt dump only — not a PASS",
            "output": r["output"][-1200:],
        }

    def resume(self) -> dict[str, Any]:
        r = self._run("init; resume")
        if not r["available"]:
            return {"available": False, "status": "UNAVAILABLE", "reason": r["reason"]}
        ok = r["returncode"] == 0
        return {"available": True, "status": "SUCCESS" if ok else "FAIL", "resumed": ok, "output": r["output"][-800:]}

    def read_register(self, name: str) -> dict[str, Any]:
        key = str(name or "").strip().lower()
        if key not in regmap.CPU_REGISTERS:
            return {
                "available": False,
                "status": "UNAVAILABLE",
                "reason": f"register {name!r} not in read-only allowlist (pc/sp/lr/xpsr)",
            }
        r = self._run(f"init; halt; reg {key}")
        if not r["available"]:
            return {"available": False, "status": "UNAVAILABLE", "reason": r["reason"], "name": key}
        words = _HEXWORD.findall(r["output"])
        value = words[-1] if words else None
        return {
            "available": True,
            "status": "UNKNOWN" if value else "UNAVAILABLE",
            "name": key,
            "value": value,
            "reason": "read only — not a PASS",
        }

    def read_memory32(self, name: str) -> dict[str, Any]:
        addr = regmap.resolve(name)
        if not addr:
            return {
                "available": False,
                "status": "UNAVAILABLE",
                "reason": f"address {name!r} not in the named register map (read-only)",
            }
        r = self._run(f"init; halt; mdw {addr} 1")
        if not r["available"]:
            return {"available": False, "status": "UNAVAILABLE", "reason": r["reason"], "name": name}
        m = _MDW_LINE.search(r["output"])
        value = f"0x{m.group(1)}" if m else None
        return {
            "available": True,
            "status": "UNKNOWN" if value else "UNAVAILABLE",
            "name": str(name).upper(),
            "address": addr,
            "value": value,
            "reason": "read only — not a PASS",
        }
