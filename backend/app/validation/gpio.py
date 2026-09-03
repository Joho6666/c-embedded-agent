from __future__ import annotations

from pathlib import Path
from typing import Any

from app.validation.base import core_source_text, result_from_checks


def validate_gpio(root: Path, pin: str = "PC13") -> dict[str, Any]:
    port = "GPIOC" if pin.upper().startswith("PC") else "GPIOA" if pin.upper().startswith("PA") else "GPIOB"
    pin_macro = f"GPIO_PIN_{pin[2:]}" if len(pin) >= 3 and pin[2:].isdigit() else "GPIO_PIN_13"
    clk = {
        "GPIOA": "__HAL_RCC_GPIOA_CLK_ENABLE",
        "GPIOB": "__HAL_RCC_GPIOB_CLK_ENABLE",
        "GPIOC": "__HAL_RCC_GPIOC_CLK_ENABLE",
    }.get(port, "__HAL_RCC_GPIOC_CLK_ENABLE")
    text = core_source_text(root)
    checks = {
        "gpio_clock": clk in text,
        "gpio_init": "HAL_GPIO_Init" in text,
        "pin_match": pin_macro in text and port in text,
        "mx_gpio": "MX_GPIO_Init" in text,
    }
    out = result_from_checks(checks)
    out["task"] = "gpio"
    out["pin"] = pin
    return out
