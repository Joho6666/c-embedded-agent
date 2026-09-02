"""Machine-checkable embedded C / ISR review (inspired by embedded-review checklists).

Only Core/ user code. Drivers/ are not scanned. HAL_Delay in main() is allowed.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.validation.base import core_source_text, result_from_checks

_ISR_NAME = re.compile(
    r"\b((?:[A-Za-z0-9_]+_IRQHandler)|(?:HAL_[A-Za-z0-9_]+_Callback))\s*\([^;]*\)\s*\{",
    re.M,
)
_FAULT_HANDLERS = {
    "HardFault_Handler",
    "MemManage_Handler",
    "BusFault_Handler",
    "UsageFault_Handler",
    "NMI_Handler",
}
_UNSAFE_ISR = (
    ("hal_delay", re.compile(r"\bHAL_Delay\s*\(")),
    ("unsafe_str", re.compile(r"\b(?:strcpy|sprintf|gets|strcat)\s*\(")),
    ("heap", re.compile(r"\b(?:malloc|calloc|realloc|free)\s*\(")),
)
_SPIN = re.compile(r"\bwhile\s*\(\s*1\s*\)")


def _body_at(text: str, brace_open: int) -> str:
    depth = 0
    for i in range(brace_open, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[brace_open : i + 1]
    return text[brace_open:]


def iter_isr_bodies(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for m in _ISR_NAME.finditer(text):
        name = m.group(1)
        body = _body_at(text, m.end() - 1)
        out.append((name, body))
    return out


def review_isrs(root: Path) -> dict[str, Any]:
    text = core_source_text(root)
    bodies = iter_isr_bodies(text)
    unsafe_delay = False
    unsafe_str = False
    unsafe_heap = False
    spin_in_isr = False
    for name, body in bodies:
        if name in _FAULT_HANDLERS:
            continue
        if _UNSAFE_ISR[0][1].search(body):
            unsafe_delay = True
        if _UNSAFE_ISR[1][1].search(body):
            unsafe_str = True
        if _UNSAFE_ISR[2][1].search(body):
            unsafe_heap = True
        if _SPIN.search(body):
            spin_in_isr = True
    checks = {
        "isr_no_hal_delay": not unsafe_delay,
        "isr_no_unsafe_string": not unsafe_str,
        "isr_no_heap": not unsafe_heap,
        "isr_no_spinloop": not spin_in_isr,
    }
    out = result_from_checks(checks)
    out["task"] = "review"
    out["severity"] = "P0" if (unsafe_delay or unsafe_str or unsafe_heap or spin_in_isr) else "ok"
    return out


def review_project(root: Path) -> dict[str, Any]:
    return review_isrs(root)
