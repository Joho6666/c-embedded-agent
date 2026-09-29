"""Simulation layer — LEVEL 2 verification (Compile → Simulation → Hardware).

A SimulationAdapter runs the real firmware ELF against a functional
emulator and collects UART/register evidence. Simulation PASS is reported
separately from Build PASS and Hardware PASS — it never substitutes either.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

ADAPTER_STATUS = ("SUPPORTED", "NOT_INSTALLED", "NOT_SUPPORTED")


class SimulationAdapter(ABC):
    id: str = "base"
    label: str = "base"
    adapter_status: str = "NOT_SUPPORTED"

    @abstractmethod
    def detect(self) -> dict[str, Any]:
        """Report emulator availability. Missing tool = NOT_INSTALLED."""

    @abstractmethod
    def run(
        self,
        elf_path: str,
        *,
        platform: str | None = None,
        uart_output_log: str | None = None,
        expect: str | None = None,
        timeout_s: float = 20.0,
    ) -> dict[str, Any]:
        """Run the ELF and collect UART evidence.

        Returns an envelope with:
        - available / status (UNAVAILABLE when the tool is missing)
        - uartLines (observed output) when a log backend exists
        - expectMatch (bool) when `expect` given
        - evidence: EvidenceRecord-ready dict (level=SIMULATION)
        """

    @abstractmethod
    def stop(self) -> dict[str, Any]:
        """Terminate the emulation."""


def _evidence(claim: str, passed: bool | None, method: str, detail: Any = None) -> dict[str, Any]:
    from app.hardware.evidence import make_evidence

    return make_evidence(claim, level="SIMULATION", passed=passed, method=method, detail=detail)
