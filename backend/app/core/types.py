from __future__ import annotations

from typing import Any, Literal

SideEffect = Literal["READ_ONLY", "MUTATING", "HARDWARE_ACTION"]

Status = Literal[
    "SUCCESS",
    "FAIL",
    "PASS",
    "WARNING",
    "PARTIAL",
    "UNKNOWN",
    "UNAVAILABLE",
]

SIDE_EFFECT_READ = "READ_ONLY"
SIDE_EFFECT_MUTATING = "MUTATING"
SIDE_EFFECT_HARDWARE = "HARDWARE_ACTION"
READ_ONLY = SIDE_EFFECT_READ
MUTATING = SIDE_EFFECT_MUTATING
HARDWARE_ACTION = SIDE_EFFECT_HARDWARE

SUCCESS = "SUCCESS"
FAIL = "FAIL"
PASS = "PASS"
WARNING = "WARNING"
PARTIAL = "PARTIAL"
UNKNOWN = "UNKNOWN"
UNAVAILABLE = "UNAVAILABLE"


def envelope(
    *,
    status: Status,
    side_effect: SideEffect,
    **extra: Any,
) -> dict[str, Any]:
    out: dict[str, Any] = {"status": status, "side_effect": side_effect}
    out.update(extra)
    return out
