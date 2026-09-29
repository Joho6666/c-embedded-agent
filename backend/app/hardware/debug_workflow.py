"""Debugger workflow — "程序烧进去以后没有输出" without guessing.

Deterministic pipeline: build → flash → reset → serial check →
halt → read PC/SP + fault registers → CrashEvidence → diagnosis.
The LLM may explain the CrashEvidence afterwards; it may not skip steps.

Every dependency (probe adapter, serial wait) is injectable so the workflow
is unit-testable without hardware and degrades to honest UNAVAILABLE.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app.core.build import build_project_at
from app.hardware import crash as crash_mod
from app.hardware.probes.base import DebugProbeAdapter

SerialWaitFn = Callable[[float], list[str]]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _step(name: str, **extra: Any) -> dict[str, Any]:
    return {"step": name, "at": _now(), **extra}


def diagnose_no_output(
    root: Path,
    probe: DebugProbeAdapter | None = None,
    serial_wait: SerialWaitFn | None = None,
    serial_timeout_s: float = 6.0,
    task: str = "",
) -> dict[str, Any]:
    """Full live-diagnosis pipeline. Returns steps + CrashEvidence when found."""
    root = Path(root)
    probe = probe if probe is not None else _default_probe()
    steps: list[dict[str, Any]] = []

    # 1. Build
    build = build_project_at(root)
    build_ok = build.get("status") == "SUCCESS" or bool(build.get("success"))
    steps.append(
        _step("build", status=build.get("status"), success=build_ok, reason=build.get("reason"))
    )
    if not build_ok:
        return {
            "status": "FAIL",
            "reason": "build failed — fix compile errors before hardware debugging",
            "steps": steps,
            "crashEvidence": None,
        }

    # 2. Flash
    elf = root / "firmware.elf"
    flash = probe.flash(str(elf)) if probe else {"available": False, "status": "UNAVAILABLE", "reason": "no probe"}
    steps.append(_step("flash", status=flash.get("status"), success=flash.get("success"), reason=flash.get("reason")))
    if not flash.get("success"):
        return {
            "status": "UNAVAILABLE" if flash.get("status") == "UNAVAILABLE" else "FAIL",
            "reason": flash.get("reason") or "flash failed",
            "steps": steps,
            "crashEvidence": None,
        }

    # 3. Reset
    reset = probe.reset("run") if probe else {"available": False}
    steps.append(_step("reset", status=reset.get("status"), success=reset.get("success")))

    # 4. Serial check
    serial_lines: list[str] = []
    serial_ok = False
    if serial_wait is not None:
        serial_lines = serial_wait(serial_timeout_s) or []
        serial_ok = bool(serial_lines)
    steps.append(_step("serial", received=bool(serial_ok), lines=serial_lines[:50]))

    if serial_ok:
        return {
            "status": "PARTIAL",
            "reason": "serial output received — hardware produced output; validate content separately",
            "steps": steps,
            "crashEvidence": None,
        }

    # 5. Halt + registers (target produced no output: look inside)
    halt = probe.halt() if probe else {"available": False}
    steps.append(_step("halt", status=halt.get("status"), halted=halt.get("halted")))
    if not halt.get("halted"):
        return {
            "status": "UNAVAILABLE" if halt.get("status") == "UNAVAILABLE" else "UNKNOWN",
            "reason": halt.get("reason") or "could not halt target — no debugger evidence available",
            "steps": steps,
            "crashEvidence": None,
        }

    pc = probe.read_register("pc") if probe else {}
    sp = probe.read_register("sp") if probe else {}
    regs = {
        "cfsr": (probe.read_memory32("CFSR") or {}).get("value"),
        "hfsr": (probe.read_memory32("HFSR") or {}).get("value"),
        "mmfar": (probe.read_memory32("MMFAR") or {}).get("value"),
        "bfar": (probe.read_memory32("BFAR") or {}).get("value"),
        "pc": pc.get("value"),
        "sp": sp.get("value"),
    }
    steps.append(_step("read_registers", registers={k: v for k, v in regs.items()}))

    readable = any(v for v in regs.values())
    if not readable:
        return {
            "status": "UNKNOWN",
            "reason": "halted but no register evidence readable",
            "steps": steps,
            "crashEvidence": None,
        }

    evidence = crash_mod.decode_fault(**regs)
    evidence["collectedBy"] = getattr(probe, "id", "unknown")
    evidence["task"] = task
    return {
        "status": "PARTIAL",
        "reason": "no serial output; fault registers decoded — see crashEvidence",
        "steps": steps,
        "crashEvidence": evidence,
    }


def _default_probe() -> DebugProbeAdapter | None:
    from app.hardware.probes import get_probe

    try:
        return get_probe("openocd")
    except KeyError:
        return None
