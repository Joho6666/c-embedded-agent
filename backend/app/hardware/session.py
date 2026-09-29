"""HardwareRun records — replayable, hash-anchored hardware sessions.

One HardwareRun documents a full hardware attempt: which firmware bytes
(sha256), which toolchain, which probe, what flash/reset produced, what the
serial line saw, what debug/hardware evidence was collected, and a final
status from a closed vocabulary.

PASS gate: `finalize_run(run, "PASS")` refuses unless flash succeeded and at
least one hardware-evidence item with `level == "HARDWARE"` was recorded as
passed. Compile-only or serial-only evidence can never finalize as PASS.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RUN_STATUSES = ("PASS", "FAIL", "PARTIAL", "UNKNOWN", "UNAVAILABLE")
EVIDENCE_LEVELS = ("BUILD", "SIMULATION", "HARDWARE", "DEBUGGER", "USER_CONFIRM")


class HardwareRunError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def git_commit(project_root: Path) -> str | None:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
            shell=False,
        )
        out = (r.stdout or "").strip()
        return out if r.returncode == 0 and out else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def create_run(
    project_root: Path,
    session: dict[str, Any] | None = None,
    platform: str = "stm32",
    toolchain_version: str | None = None,
) -> dict[str, Any]:
    session = session or {}
    project_root = Path(project_root)
    run: dict[str, Any] = {
        "runId": f"hw-{uuid.uuid4().hex[:12]}",
        "projectId": project_root.name,
        "platform": platform,
        "board": session.get("board"),
        "mcu": session.get("mcu"),
        "firmwareHash": _sha256(project_root / "firmware.bin"),
        "elfHash": _sha256(project_root / "firmware.elf"),
        "gitCommit": git_commit(project_root),
        "toolchain": "arm-none-eabi-gcc",
        "toolchainVersion": toolchain_version,
        "debugProbe": session.get("debugger") or session.get("debugProbe"),
        "probeSerial": session.get("probeSerial") or session.get("debugProbeSerial"),
        "serialDevice": session.get("serialDevice"),
        "baud": session.get("baud", 115200),
        "flashCommand": None,
        "flashResult": None,
        "resetResult": None,
        "serialLog": [],
        "debugEvidence": [],
        "hardwareEvidence": [],
        "startedAt": _now(),
        "finishedAt": None,
        "status": "UNKNOWN",
    }
    return run


def set_flash_result(run: dict[str, Any], command: str, result: dict[str, Any]) -> None:
    run["flashCommand"] = command
    run["flashResult"] = {
        "success": bool(result.get("success")),
        "exitCode": result.get("exit_code"),
        "output": (result.get("output") or "")[-4000:],
        "at": _now(),
    }


def set_reset_result(run: dict[str, Any], result: dict[str, Any]) -> None:
    run["resetResult"] = {
        "success": bool(result.get("success")),
        "detail": (result.get("detail") or result.get("output") or "")[-1000:],
        "at": _now(),
    }


def set_serial_log(run: dict[str, Any], lines: list[str]) -> None:
    run["serialLog"] = [str(x) for x in (lines or [])][:2000]


def add_evidence(run: dict[str, Any], level: str, item: dict[str, Any]) -> None:
    if level not in EVIDENCE_LEVELS:
        raise HardwareRunError(f"invalid evidence level: {level!r}")
    entry = {"level": level, "at": _now(), **item}
    if level in ("DEBUGGER", "BUILD", "SIMULATION"):
        run["debugEvidence"].append(entry)
    else:
        run["hardwareEvidence"].append(entry)


def finalize_run(run: dict[str, Any], status: str) -> dict[str, Any]:
    if status not in RUN_STATUSES:
        raise HardwareRunError(f"invalid hardware run status: {status!r} (allowed: {RUN_STATUSES})")
    if status == "PASS":
        if not (run.get("flashResult") or {}).get("success"):
            raise HardwareRunError("PASS requires a successful flash result")
        confirmed = [
            e
            for e in run.get("hardwareEvidence") or []
            if e.get("level") == "HARDWARE" and e.get("passed") is True
        ]
        if not confirmed:
            raise HardwareRunError(
                "PASS requires at least one hardware-evidence item marked passed "
                "(serial token / GPIO / debugger sample / user confirmation)"
            )
    run["status"] = status
    run["finishedAt"] = _now()
    return run


def runs_dir(project_root: Path) -> Path:
    return Path(project_root) / "hardware-runs"


def save_run(project_root: Path, run: dict[str, Any]) -> Path:
    d = runs_dir(project_root)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{run['runId']}.json"
    path.write_text(json.dumps(run, indent=2), encoding="utf-8")
    (d / "latest.json").write_text(json.dumps({"runId": run["runId"]}, indent=2), encoding="utf-8")
    return path


def load_runs(project_root: Path) -> list[dict[str, Any]]:
    d = runs_dir(project_root)
    if not d.is_dir():
        return []
    out = []
    for p in sorted(d.glob("hw-*.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return out


def load_run(project_root: Path, run_id: str) -> dict[str, Any] | None:
    p = runs_dir(project_root) / f"{run_id}.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
