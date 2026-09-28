"""Device backend contract shared by the virtual board and real probes.

A backend turns "load this ELF and run it" into observable state: serial lines,
pin levels and a running/stopped flag. The ``DeviceService`` owns one backend,
drives it from a background thread and keeps the history that makes up the
"latest state" an engineer (or an agent) can query at any time.

Evidence is always labelled: ``SIMULATED`` for the virtual board, ``HARDWARE``
for a real probe. A backend that has never been validated on real hardware
reports ``validated: False`` in ``info()``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any

SerialSink = Callable[[str, str], None]  # (channel, text chunk)

# STM32F1 GPIO register map (RM0008): port base, IDR/ODR offsets.
STM32F1_GPIO_BASE = {"A": 0x40010800, "B": 0x40010C00, "C": 0x40011000, "D": 0x40011400, "E": 0x40011800}
GPIO_IDR, GPIO_ODR = 0x08, 0x0C


def parse_pin(pin: str) -> tuple[str, int]:
    """'PC13' / 'C13' -> ('C', 13)."""
    text = pin.strip().upper().removeprefix("P")
    port, number = text[0], int(text[1:])
    if port not in STM32F1_GPIO_BASE or not 0 <= number <= 15:
        raise ValueError(f"unsupported pin: {pin}")
    return port, number


class DeviceError(RuntimeError):
    pass


class DeviceBackend(ABC):
    kind: str = "abstract"  # "virtual" | "hardware"
    evidence: str = "UNAVAILABLE"  # "SIMULATED" | "HARDWARE"

    def __init__(self) -> None:
        self.sink: SerialSink | None = None

    @abstractmethod
    def available(self) -> tuple[bool, str | None]:
        """Whether this backend can run here, and why not."""

    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def flash(self, elf: Path) -> dict[str, Any]:
        """Load and start firmware. Must not report success without evidence."""

    @abstractmethod
    def reset(self) -> dict[str, Any]: ...

    @abstractmethod
    def tick(self) -> None:
        """Called periodically by the service: advance time / poll I/O."""

    def write_serial(self, text: str, channel: str = "usart1") -> dict[str, Any]:
        return {"ok": False, "reason": "serial write unsupported"}

    def read_pins(self, pins: list[str]) -> dict[str, dict[str, Any]]:
        return {pin: {"level": None, "reason": "pin read unsupported"} for pin in pins}

    def info(self) -> dict[str, Any]:
        return {"kind": self.kind, "evidence": self.evidence}

    def close(self) -> None: ...

    def emit_serial(self, channel: str, text: str) -> None:
        if self.sink and text:
            self.sink(channel, text)
