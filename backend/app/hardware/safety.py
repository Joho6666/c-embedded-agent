"""Hardware action safety — DANGEROUS_HARDWARE policy and power control.

Dangerous operations are BLOCKED by default. They execute only after an
explicit approval token recorded in the approvals registry. There is no
auto-approval and no per-session blanket grant.

PowerControllerAdapter is interface-only until a real device (USB relay /
smart plug / lab PSU) is actually connected — no fake implementations.
"""

from __future__ import annotations

from typing import Any

DANGEROUS_OPERATIONS = (
    "mass_erase",
    "option_bytes_write",
    "flash_protection_change",
    "bootloader_overwrite",
    "write_memory",
    "power_cycle",
)

# Approval levels (v0.10 unified model; approval engine integration in Phase I)
LEVELS = {
    "SAFE_READ": "auto",
    "SAFE_BUILD": "auto",
    "PROJECT_WRITE": "ask_once",
    "HARDWARE_FLASH": "ask_once",
    "DEBUG_CONTROL": "auto",
    "GIT_WRITE": "auto",
    "DANGEROUS_HARDWARE": "deny",
    "EXTERNAL_WRITE": "ask_every_time",
    "SYSTEM_CHANGE": "deny",
}

# operations → required approval level
OPERATION_LEVEL = {
    "mass_erase": "DANGEROUS_HARDWARE",
    "option_bytes_write": "DANGEROUS_HARDWARE",
    "flash_protection_change": "DANGEROUS_HARDWARE",
    "bootloader_overwrite": "DANGEROUS_HARDWARE",
    "write_memory": "DEBUG_CONTROL",
    "power_cycle": "HARDWARE_FLASH",
}


# single-use approval tokens: "{operation}:{token}"
_APPROVED: set[str] = set()


def approve_operation(operation: str, token: str) -> dict[str, Any]:
    """Record an explicit approval token (issued by a human confirmation)."""
    if operation not in DANGEROUS_OPERATIONS:
        raise ValueError(f"unknown dangerous operation: {operation!r}")
    if not token or len(token) < 6:
        raise ValueError("approval token too short")
    _APPROVED.add(f"{operation}:{token}")
    return {"operation": operation, "approved": True}


def revoke_all() -> None:
    _APPROVED.clear()


def check_operation(operation: str, token: str | None = None) -> dict[str, Any]:
    """Policy gate for hardware operations. Dangerous ops default BLOCKED."""
    level = OPERATION_LEVEL.get(operation)
    if level is None:
        return {"allowed": False, "level": None, "reason": f"unknown operation: {operation!r}"}
    if level == "DANGEROUS_HARDWARE":
        key = f"{operation}:{token}" if token else None
        if key and key in _APPROVED:
            _APPROVED.discard(key)  # single use
            return {"allowed": True, "level": level, "reason": "explicit approval token"}
        return {
            "allowed": False,
            "level": level,
            "reason": f"{operation} is DANGEROUS_HARDWARE: BLOCKED by default, requires explicit approval",
        }
    if level in ("HARDWARE_FLASH", "DEBUG_CONTROL"):
        # flash and debug control are gated upstream (confirm flags / budget);
        # direct calls here are allowed but logged as hardware actions.
        return {"allowed": True, "level": level, "reason": f"{level}: gated upstream by confirm/flash-budget"}
    return {"allowed": False, "level": level, "reason": f"{level}: not permitted without the approval engine"}


class PowerControllerAdapter:
    """Interface only. Real adapters arrive with a real device; until then
    every method returns UNAVAILABLE — never a simulated power action."""

    id = "none"

    def power_on(self) -> dict[str, Any]:
        return self._unavailable("power_on")

    def power_off(self) -> dict[str, Any]:
        return self._unavailable("power_off")

    def power_cycle(self, token: str | None = None) -> dict[str, Any]:
        gate = check_operation("power_cycle")
        if not gate["allowed"]:
            return {"available": False, "status": "UNAVAILABLE", "reason": gate["reason"]}
        return self._unavailable("power_cycle")

    def is_powered(self) -> dict[str, Any]:
        return {"available": False, "status": "UNAVAILABLE", "reason": "no power controller device configured"}

    def _unavailable(self, op: str) -> dict[str, Any]:
        return {
            "available": False,
            "status": "UNAVAILABLE",
            "reason": f"{op}: no power controller device configured (interface only)",
        }
