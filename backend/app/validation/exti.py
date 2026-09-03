from __future__ import annotations

from pathlib import Path
from typing import Any

from app.validation.base import core_source_text, result_from_checks


def validate_exti(root: Path) -> dict[str, Any]:
    text = core_source_text(root)
    checks = {
        "gpio_input": "GPIO_MODE_IT_FALLING" in text or "GPIO_MODE_IT_RISING" in text or "GPIO_MODE_IT_RISING_FALLING" in text,
        "exti_edge": "GPIO_MODE_IT_" in text,
        "nvic": "HAL_NVIC_EnableIRQ" in text and "EXTI" in text,
        "irq_handler": "EXTI" in text and "IRQHandler" in text,
        "callback": "HAL_GPIO_EXTI_Callback" in text,
    }
    out = result_from_checks(checks)
    out["task"] = "exti"
    return out
