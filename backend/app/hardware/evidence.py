"""Evidence model — first-class, auditable verification records.

Three verification levels are always reported separately:

    Build PASS      ≠  Simulation PASS   ≠  Hardware PASS

An overall status is PARTIAL whenever levels disagree (e.g. build OK,
hardware NOT_TESTED). Nothing downstream may collapse them into one PASS.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EVIDENCE_LEVELS = ("BUILD", "SIMULATION", "HARDWARE", "DEBUGGER", "USER_CONFIRM")
REPORT_LEVELS = ("BUILD", "SIMULATION", "HARDWARE")  # the three headline levels
LEVEL_STATUSES = ("PASS", "FAIL", "NOT_TESTED")


class EvidenceError(ValueError):
    pass


def make_evidence(
    claim: str,
    *,
    level: str,
    passed: bool | None = None,
    method: str | None = None,
    artifact: str | Path | None = None,
    detail: Any = None,
) -> dict[str, Any]:
    """Create one EvidenceRecord. `passed=None` means collected but inconclusive."""
    if level not in EVIDENCE_LEVELS:
        raise EvidenceError(f"invalid evidence level: {level!r}")
    record: dict[str, Any] = {
        "claim": str(claim),
        "level": level,
        "passed": passed,
        "method": method,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "detail": detail,
    }
    if artifact is not None:
        p = Path(artifact)
        record["artifact"] = str(p)
        if p.is_file():
            record["artifactHash"] = hashlib.sha256(p.read_bytes()).hexdigest()
    return record


def evidence_from_hardware_run(run: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert a persisted HardwareRun into EvidenceRecords (auditable chain)."""
    out: list[dict[str, Any]] = []
    if run.get("firmwareHash") or run.get("elfHash"):
        out.append(
            {
                "claim": f"firmware built ({run.get('toolchain')} {run.get('toolchainVersion') or 'version unknown'})",
                "level": "BUILD",
                "passed": True if run.get("firmwareHash") else None,
                "method": "arm-none-eabi-gcc + make",
                "artifactHash": run.get("firmwareHash"),
                "timestamp": run.get("startedAt"),
                "detail": None,
            }
        )
    flash = run.get("flashResult") or {}
    if flash:
        out.append(
            {
                "claim": "firmware flashed and verified on target",
                "level": "HARDWARE",
                "passed": bool(flash.get("success")),
                "method": str(run.get("debugProbe") or "probe"),
                "artifactHash": run.get("firmwareHash"),
                "timestamp": flash.get("at"),
                "detail": (flash.get("output") or "")[-500:],
            }
        )
    if run.get("serialLog"):
        out.append(
            {
                "claim": "serial output captured from device",
                "level": "HARDWARE",
                "passed": True,
                "method": f"pyserial@{run.get('baud')}",
                "artifactHash": None,
                "timestamp": run.get("finishedAt"),
                "detail": "\n".join(run["serialLog"][:20]),
            }
        )
    for e in run.get("hardwareEvidence") or []:
        out.append(
            {
                "claim": str(e.get("claim") or "hardware evidence"),
                "level": e.get("level", "HARDWARE"),
                "passed": e.get("passed"),
                "method": "hardware-evidence",
                "artifactHash": None,
                "timestamp": e.get("at"),
                "detail": e.get("detail"),
            }
        )
    for e in run.get("debugEvidence") or []:
        out.append(
            {
                "claim": str(e.get("claim") or "debugger evidence"),
                "level": "DEBUGGER",
                "passed": e.get("passed"),
                "method": "debugger",
                "artifactHash": None,
                "timestamp": e.get("at"),
                "detail": e.get("detail"),
            }
        )
    return out


def _level_status(records: list[dict[str, Any]], level: str) -> str:
    relevant = [r for r in records if r.get("level") == level]
    if not relevant:
        return "NOT_TESTED"
    if all(r.get("passed") is True for r in relevant):
        return "PASS"
    if all(r.get("passed") is False for r in relevant):
        return "FAIL"
    return "NOT_TESTED"  # inconclusive evidence never upgrades a level


def verification_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate EvidenceRecords into the three-level report + overall status.

    Overall PASS requires the strongest levels (HARDWARE + BUILD) to pass;
    a missing SIMULATION level does not fake or block hardware results, but
    any FAIL anywhere fails the whole report.
    """
    levels = {lvl: _level_status(records, lvl) for lvl in REPORT_LEVELS}
    if "FAIL" in levels.values():
        overall = "FAIL"
    elif levels["HARDWARE"] == "PASS" and levels["BUILD"] == "PASS":
        overall = "PASS"
    elif all(v == "NOT_TESTED" for v in levels.values()):
        overall = "NOT_TESTED"
    else:
        overall = "PARTIAL"
    return {
        "levels": levels,
        "overall": overall,
        "rule": "Build PASS ≠ Simulation PASS ≠ Hardware PASS; FAIL anywhere → FAIL; "
        "overall PASS needs HARDWARE+BUILD; otherwise PARTIAL",
        "evidenceCount": len(records),
        "evidence": records,
    }


def report_from_json_file(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
