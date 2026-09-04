from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.build import build_project_at, diagnose_build_at
from app.core.flash import flash_firmware_at
from app.core.periph import configure_peripheral_at
from app.core.project import check_pin_conflicts_at, get_board_context_at, inspect_project_at, parse_ioc_at
from app.core.validation import validate_hardware_at


class STM32Adapter:
    id = "stm32"

    def detect(self, root: Path) -> bool:
        if not root.is_dir():
            return False
        if list(root.glob("*.ioc")):
            return True
        names = [p.name.lower() for p in root.iterdir()]
        if any("stm32f103" in n or n.startswith("startup_stm32f1") for n in names):
            return True
        makefile = root / "Makefile"
        if makefile.is_file():
            try:
                text = makefile.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            if "STM32F1" in text or "stm32f1" in text:
                return True
        return (root / "Drivers" / "STM32F1xx_HAL_Driver").is_dir()

    def inspect(self, root: Path) -> dict[str, Any]:
        return inspect_project_at(root)

    def parse_ioc(self, root: Path, ioc_path: str | None = None) -> dict[str, Any]:
        return parse_ioc_at(root, ioc_path)

    def check_pin_conflicts(self, root: Path) -> dict[str, Any]:
        return check_pin_conflicts_at(root)

    def board_context(self, root: Path) -> dict[str, Any]:
        return get_board_context_at(root)

    def build(self, root: Path) -> dict[str, Any]:
        return build_project_at(root)

    def diagnose(self, root: Path, log: str | None = None) -> dict[str, Any]:
        return diagnose_build_at(root, log)

    def flash(self, root: Path) -> dict[str, Any]:
        return flash_firmware_at(root)

    def validate(
        self,
        root: Path,
        *,
        serial_device: str | None = None,
        baud: int = 115200,
        expect: str | None = None,
        task: str = "",
    ) -> dict[str, Any]:
        return validate_hardware_at(
            root,
            serial_device=serial_device,
            baud=baud,
            expect=expect,
            task=task,
        )

    def configure_peripheral(self, root: Path, kind: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        return configure_peripheral_at(root, kind, args)
