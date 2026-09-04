from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class PlatformAdapter(Protocol):
    """Minimal adapter surface for the current STM32F103 runtime.

    Only methods STM32 actually needs today. Empty ESP32/C51 adapters are
    intentionally not defined.
    """

    id: str

    def detect(self, root: Path) -> bool: ...

    def inspect(self, root: Path) -> dict[str, Any]: ...

    def parse_ioc(self, root: Path, ioc_path: str | None = None) -> dict[str, Any]: ...

    def check_pin_conflicts(self, root: Path) -> dict[str, Any]: ...

    def board_context(self, root: Path) -> dict[str, Any]: ...

    def build(self, root: Path) -> dict[str, Any]: ...

    def diagnose(self, root: Path, log: str | None = None) -> dict[str, Any]: ...

    def flash(self, root: Path) -> dict[str, Any]: ...

    def validate(
        self,
        root: Path,
        *,
        serial_device: str | None = None,
        baud: int = 115200,
        expect: str | None = None,
        task: str = "",
    ) -> dict[str, Any]: ...

    def configure_peripheral(self, root: Path, kind: str, args: dict[str, Any] | None = None) -> dict[str, Any]: ...
