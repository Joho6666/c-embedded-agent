"""DebugProbeAdapter abstraction.

A probe adapter wraps one physical debug probe family (OpenOCD+ST-Link today;
pyOCD / J-Link only when they have been really tested). Every method returns
an honest envelope: `{"available": bool, "status": ..., "reason": ...}`.
Nothing here ever reports a PASS — probes move hardware, evidence is
collected by the evidence layer (Phase E).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

# Adapter capability declarations are honest: SUPPORTED requires a real test
# on this repo's hardware lab. NOT_SUPPORTED is a promise not to pretend.
ADAPTER_STATUS = ("SUPPORTED", "NOT_SUPPORTED", "NOT_INSTALLED")


class DebugProbeAdapter(ABC):
    id: str = "base"
    label: str = "base"
    adapter_status: str = "NOT_SUPPORTED"

    @abstractmethod
    def detect(self) -> dict[str, Any]:
        """Probe presence + tool installation. Never Connected when absent."""

    @abstractmethod
    def identify_target(self) -> dict[str, Any]:
        """SWD/JTAG chip-id read. Family-level evidence at best."""

    @abstractmethod
    def flash(self, elf_path: str) -> dict[str, Any]:
        """Program + verify. HARDWARE_ACTION side effect."""

    @abstractmethod
    def reset(self, mode: str = "run") -> dict[str, Any]:
        """reset run / halt."""

    @abstractmethod
    def halt(self) -> dict[str, Any]:
        """Halt the core. Prerequisite for register/memory reads."""

    @abstractmethod
    def resume(self) -> dict[str, Any]:
        """Resume from halt."""

    @abstractmethod
    def read_register(self, name: str) -> dict[str, Any]:
        """Read a register from the frozen allowlist (SCB/PC/SP/LR/...)."""

    @abstractmethod
    def read_memory32(self, name: str) -> dict[str, Any]:
        """Read one 32-bit word from a named, allowlisted address."""

    def write_memory32(self, name: str, value: int) -> dict[str, Any]:
        return {
            "available": False,
            "status": "UNAVAILABLE",
            "reason": "register writes are not enabled in read-only diagnosis mode",
        }

    def set_breakpoint(self, address: str) -> dict[str, Any]:
        return self._use_gdb_mi("set_breakpoint")

    def run_to_breakpoint(self, address: str) -> dict[str, Any]:
        return self._use_gdb_mi("run_to_breakpoint")

    def collect_trace(self) -> dict[str, Any]:
        return {
            "available": False,
            "status": "UNAVAILABLE",
            "reason": "trace (ITM/SWO) capture is not integrated yet",
        }

    def _use_gdb_mi(self, op: str) -> dict[str, Any]:
        return {
            "available": False,
            "status": "UNAVAILABLE",
            "reason": f"{op} must go through the GDB/MI DebuggerSession, not raw probe commands",
        }


def _not_installed(adapter_id: str, tool: str) -> dict[str, Any]:
    return {"available": False, "status": "UNAVAILABLE", "reason": f"{tool} not installed"}
