"""StaticAnalysisPipeline — deterministic embedded lint rules.

Complements compiler warnings / cppcheck with embedded-specific deterministic
checks. Every finding is a StaticFinding {rule, severity, file, line,
evidence, fixability}; severities are ERROR / WARNING / INFO — only ERROR is
treated as blocking by the pipeline. These rules never consult an LLM.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

SEVERITIES = ("ERROR", "WARNING", "INFO")

# ISR body extraction: `void XYZ_IRQHandler(void) { ... }` with brace matching
_ISR_RE = re.compile(r"void\s+(\w+_IRQHandler)\s*\([^)]*\)\s*\{")

BLOCKING_CALLS = ("HAL_Delay(", "printf(", "sprintf(", "vTaskDelay(")
UNSAFE_CALLS = ("gets(", "strcpy(", "strcat(", "sprintf(")
LOCAL_ARRAY_RE = re.compile(r"^\s*(?:static\s+)?(?:const\s+)?(?:unsigned\s+)?(?:char|uint8_t|int8_t|int|uint16_t|int16_t|uint32_t|int32_t)\s+\w+\s*\[\s*(\d+)\s*\]", re.MULTILINE)
VOLATILE_DECL_RE = re.compile(r"^\s*(?!.*\bvolatile\b).*\b(bool|uint8_t|uint16_t|uint32_t|int)\s+(\w+)\s*(?:=\s*[^;]+)?;\s*$")
BUSY_WAIT_RE = re.compile(r"for\s*\(\s*volatile\s+\w+\s+\w+\s*=\s*0\s*;\s*\w+\s*<\s*\d+")


def _isr_bodies(text: str) -> list[tuple[str, int, str]]:
    out: list[tuple[str, int, str]] = []
    for m in _ISR_RE.finditer(text):
        start = m.end() - 1
        depth = 0
        body_start = start
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    out.append((m.group(1), text.count("\n", 0, body_start) + 1, text[body_start : i + 1]))
                    break
    return out


def _line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def lint_source(path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    findings: list[dict[str, Any]] = []

    def add(rule: str, severity: str, line: int, evidence: str, fixability: str) -> None:
        findings.append(
            {
                "rule": rule,
                "severity": severity,
                "file": str(path),
                "line": line,
                "evidence": evidence[:160],
                "fixability": fixability,
            }
        )

    # 1. Blocking / heavy calls inside ISR bodies — deterministic ERROR
    for name, line, body in _isr_bodies(text):
        for call in BLOCKING_CALLS:
            idx = body.find(call)
            if idx >= 0:
                add(
                    "isr-blocking-call",
                    "ERROR",
                    line + body[:idx].count("\n"),
                    f"{name} contains {call}) — blocking call in interrupt context",
                    "mechanical: move work to main loop via flag",
                )
        for call in UNSAFE_CALLS:
            idx = body.find(call)
            if idx >= 0:
                add(
                    "isr-unsafe-string",
                    "ERROR",
                    line + body[:idx].count("\n"),
                    f"{name} contains {call}) — unbounded string op in ISR",
                    "manual",
                )

    # 2. Unsafe string functions anywhere — ERROR for gets, WARNING for others
    for call in UNSAFE_CALLS:
        for m in re.finditer(re.escape(call), text):
            sev = "ERROR" if call == "gets(" else "WARNING"
            add(
                "unsafe-string-fn" if call != "gets(" else "unsafe-gets",
                sev,
                _line_of(text, m.start()),
                f"{call} — use bounded alternatives (snprintf/strncpy)",
                "mechanical for sprintf→snprintf with size",
            )

    # 3. Stack-heavy local arrays — WARNING
    for m in LOCAL_ARRAY_RE.finditer(text):
        size = int(m.group(1))
        if size >= 256:
            add(
                "stack-heavy-array",
                "WARNING",
                _line_of(text, m.start()),
                f"local array of {size} bytes — stack pressure (20K RAM on C8T6)",
                "mechanical: move to static/global or shrink",
            )

    # 4. Shared flag likely missing volatile — WARNING (heuristic, may false-positive)
    if "_IRQHandler" in text:
        decls = {
            m.group(2): _line_of(text, m.start())
            for m in VOLATILE_DECL_RE.finditer(text)
        }
        for name, line in decls.items():
            assigned = re.search(rf"\b{name}\b\s*=\s*[^;]+;", text)
            referenced = re.search(rf"\b{name}\b", text)
            if assigned and referenced:
                add(
                    "missing-volatile",
                    "WARNING",
                    line,
                    f"shared variable `{name}` declared without volatile but used with IRQ handlers",
                    "mechanical: add volatile",
                )

    # 5. Busy-wait calibration loops — INFO
    for m in BUSY_WAIT_RE.finditer(text):
        add(
            "busy-wait-loop",
            "INFO",
            _line_of(text, m.start()),
            "volatile busy-wait loop — prefer timer/SysTick time base",
            "manual",
        )

    return findings


def lint_project(root: Path) -> dict[str, Any]:
    root = Path(root)
    findings: list[dict[str, Any]] = []
    files = sorted((root / "Core" / "Src").glob("*.c")) if (root / "Core" / "Src").is_dir() else []
    if not files:
        return {
            "available": True,
            "status": "UNAVAILABLE",
            "reason": "no Core/Src sources found",
            "findings": [],
            "counts": {},
        }
    for f in files:
        findings.extend(lint_source(f))
    counts = {sev: sum(1 for x in findings if x["severity"] == sev) for sev in SEVERITIES}
    return {
        "available": True,
        "status": "FAIL" if counts["ERROR"] else ("WARNING" if counts["WARNING"] else "OK"),
        "files": [str(f) for f in files],
        "findings": findings,
        "counts": counts,
        "note": "only ERROR findings block; WARNING/INFO are advisory",
    }
