from __future__ import annotations

from pathlib import Path

from app.core.platforms.base import PlatformAdapter
from app.core.platforms.stm32 import STM32Adapter

_STM32 = STM32Adapter()


def detect_adapter(root: Path) -> PlatformAdapter:
    if _STM32.detect(root):
        return _STM32
    return _STM32


def stm32_adapter() -> STM32Adapter:
    return _STM32


__all__ = ["PlatformAdapter", "STM32Adapter", "detect_adapter", "stm32_adapter"]
