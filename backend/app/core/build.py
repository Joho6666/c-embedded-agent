from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.types import FAIL, MUTATING, READ_ONLY, SUCCESS, UNAVAILABLE, UNKNOWN, envelope
from app.tools.compiler import CompileError, compile_project
from app.tools.error_memory import match_known_errors, record_from_output
from app.tools.gcc_parser import parse_gcc_output


def _classify_issue(diag: dict[str, Any], known: list[dict[str, Any]]) -> str:
    msg = str(diag.get("message") or "")
    source = str(diag.get("source") or "")
    low = msg.lower()
    if source == "ld" or "undefined reference" in low:
        if "HAL_" in msg:
            return "missing_hal_module"
        return "undefined_symbol"
    if "multiple definition" in low:
        return "linker_error"
    if "No such file or directory" in msg or "fatal error" in low and ".h" in low:
        return "include_issue"
    if "STM32F103" in msg and "ld" in low or ".ld" in str(diag.get("file") or ""):
        return "linker_script_issue"
    if "IRQHandler" in msg:
        return "isr_conflict"
    if source == "gcc":
        return "compile_error"
    for hit in known:
        tag = str(hit.get("tag") or "").lower()
        if "linker" in tag:
            return "linker_error"
        if "hal" in tag:
            return "missing_hal_module"
        if "gpio" in tag or "pin" in tag:
            return "wrong_pin"
        if "irq" in tag:
            return "isr_conflict"
    return "compile_error"


def build_project_at(root: Path) -> dict[str, Any]:
    try:
        packed = compile_project(root)
    except CompileError as e:
        record_from_output(str(e), success=False)
        return envelope(
            status=UNAVAILABLE,
            side_effect=MUTATING,
            success=False,
            available=False,
            reason=str(e),
            exit_code=None,
            stdout="",
            stderr=str(e),
            artifacts=[],
            elf=None,
            hex=None,
            bin=None,
            size=None,
        )
    artifacts = list(packed.get("artifacts") or [])
    by_name = {a.get("name"): a for a in artifacts if isinstance(a, dict)}
    elf = root / "firmware.elf"
    hex_p = root / "firmware.hex"
    bin_p = root / "firmware.bin"
    exit_code = packed.get("exit_code")
    make_ok = bool(packed.get("success")) and exit_code == 0
    has_elf = elf.is_file()
    if make_ok and not has_elf:
        status = FAIL
        success = False
        reason = "make exited 0 but firmware.elf is missing"
    elif make_ok and has_elf:
        status = SUCCESS
        success = True
        reason = None
    else:
        status = FAIL
        success = False
        reason = "compile failed"
    combined = str(packed.get("combined") or "")
    record_from_output(combined, success=success)
    size = packed.get("memory")
    return envelope(
        status=status,
        side_effect=MUTATING,
        success=success,
        available=True,
        reason=reason,
        exit_code=exit_code,
        stdout=packed.get("stdout") or "",
        stderr=packed.get("stderr") or "",
        combined=combined,
        diagnostics=packed.get("diagnostics") or [],
        artifacts=artifacts,
        elf=str(elf) if has_elf else None,
        hex=str(hex_p) if hex_p.is_file() else None,
        bin=str(bin_p) if bin_p.is_file() else None,
        size=size,
        memory=size,
        artifact_map=by_name,
        # preserve compiler.py keys used by Web
        packed=packed,
    )


def diagnose_build_at(root: Path, log: str | None = None) -> dict[str, Any]:
    text = log or ""
    packed = None
    compile_status = None
    if not text.strip():
        return envelope(
            status=UNKNOWN,
            side_effect=READ_ONLY,
            reason="no compiler log provided — pass build stdout/stderr; diagnose does not compile",
            log_excerpt="",
            diagnostics=[],
            issues=[],
            categories=[],
            error_memory=[],
            source="deterministic_rules",
            compile_status=None,
            packed=None,
            project_root=str(root),
        )
    diagnostics = parse_gcc_output(text or "")
    known = match_known_errors(text or "")
    issues = []
    for d in diagnostics:
        issues.append(
            {
                **d,
                "category": _classify_issue(d, known),
            }
        )
    if not issues and known:
        for hit in known:
            issues.append(
                {
                    "file": (hit.get("files") or [""])[0],
                    "line": 0,
                    "severity": "error",
                    "message": hit.get("pattern"),
                    "category": _classify_issue({"message": hit.get("pattern"), "source": "ld"}, [hit]),
                    "error_memory_id": hit.get("id"),
                }
            )
    categories = sorted({str(i.get("category")) for i in issues if i.get("category")})
    if compile_status == UNAVAILABLE:
        status = UNAVAILABLE
    elif issues:
        status = FAIL
    else:
        status = SUCCESS
    return envelope(
        status=status,
        side_effect=READ_ONLY,
        log_excerpt=(text or "")[-8000:],
        diagnostics=diagnostics,
        issues=issues,
        categories=categories,
        error_memory=[{"id": h.get("id"), "tag": h.get("tag"), "rootCause": h.get("rootCause"), "fix": h.get("fix")} for h in known],
        source="deterministic_rules",
        compile_status=compile_status,
        packed=packed,
    )
