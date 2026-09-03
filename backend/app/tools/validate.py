from __future__ import annotations

from pathlib import Path
from typing import Any

from app.tools.filesystem import list_files, read_file


def validate_led_task(root: Path, pin: str = "PC13") -> dict[str, Any]:
    port = "GPIOC" if pin.upper().startswith("PC") else "GPIOA" if pin.upper().startswith("PA") else "GPIOB"
    pin_macro = f"GPIO_PIN_{pin[2:]}" if len(pin) >= 3 and pin[2:].isdigit() else "GPIO_PIN_13"
    clk = {
        "GPIOA": "__HAL_RCC_GPIOA_CLK_ENABLE",
        "GPIOB": "__HAL_RCC_GPIOB_CLK_ENABLE",
        "GPIOC": "__HAL_RCC_GPIOC_CLK_ENABLE",
    }.get(port, "__HAL_RCC_GPIOC_CLK_ENABLE")
    blobs = []
    for rel in list_files(root):
        if rel.endswith((".c", ".h")) and "Drivers/" not in rel:
            try:
                blobs.append(read_file(root, rel))
            except OSError:
                continue
    text = "\n".join(blobs)
    checks = {
        "gpio_clock": clk in text,
        "gpio_init": "HAL_GPIO_Init" in text and "MX_GPIO_Init" in text,
        "pin_match": pin_macro in text and port in text,
        "delay_500": "HAL_Delay(500)" in text or "HAL_Delay( 500 )" in text,
        "toggle": "HAL_GPIO_TogglePin" in text,
    }
    score = int(100 * sum(1 for v in checks.values() if v) / len(checks))
    return {"task": "led", "pin": pin, "checks": checks, "score": score, "passed": score == 100}


def core_source_text(root: Path) -> str:
    blobs = []
    for rel in list_files(root):
        if rel.endswith((".c", ".h")) and "Drivers/" not in rel:
            try:
                blobs.append(read_file(root, rel))
            except OSError:
                continue
    return "\n".join(blobs)


def inspect_usart(root: Path) -> dict[str, Any]:
    text = core_source_text(root)
    try:
        mk = read_file(root, "Makefile")
    except FileNotFoundError:
        mk = ""
    try:
        conf = read_file(root, "Core/Inc/stm32f1xx_hal_conf.h")
    except FileNotFoundError:
        conf = ""
    checks = {
        "usart_clock": "__HAL_RCC_USART1_CLK_ENABLE" in text,
        "gpioa_clock": "__HAL_RCC_GPIOA_CLK_ENABLE" in text,
        "hal_uart_init": "HAL_UART_Init" in text,
        "baud_115200": "115200" in text,
        "pa9": "GPIO_PIN_9" in text,
        "pa10": "GPIO_PIN_10" in text,
        "uart_source": "stm32f1xx_hal_uart.c" in mk,
        "uart_module": "HAL_UART_MODULE_ENABLED" in conf and not _commented_macro(conf, "HAL_UART_MODULE_ENABLED"),
    }
    score = int(100 * sum(1 for v in checks.values() if v) / len(checks))
    missing = [k for k, v in checks.items() if not v]
    return {"task": "usart", "checks": checks, "score": score, "passed": score == 100, "missing": missing}


def _commented_macro(conf: str, macro: str) -> bool:
    import re

    if re.search(rf"^\s*#define\s+{re.escape(macro)}\s*$", conf, re.M):
        return False
    return True
