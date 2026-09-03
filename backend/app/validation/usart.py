from __future__ import annotations

from pathlib import Path
from typing import Any

from app.validation.base import core_source_text, module_enabled, read_hal_conf, read_makefile, result_from_checks


def validate_usart(root: Path, mode: str = "polling") -> dict[str, Any]:
    text = core_source_text(root)
    mk = read_makefile(root)
    conf = read_hal_conf(root)
    checks = {
        "usart_clock": "__HAL_RCC_USART1_CLK_ENABLE" in text or "__HAL_RCC_USART2_CLK_ENABLE" in text,
        "gpio_clock": "__HAL_RCC_GPIOA_CLK_ENABLE" in text,
        "tx_pin": "GPIO_PIN_9" in text or "GPIO_PIN_2" in text,
        "rx_pin": "GPIO_PIN_10" in text or "GPIO_PIN_3" in text,
        "baud": "115200" in text or "BaudRate" in text,
        "hal_init": "HAL_UART_Init" in text,
        "msp": "HAL_UART_MspInit" in text,
        "api": "HAL_UART_Transmit" in text or "HAL_UART_Receive" in text,
        "uart_source": "stm32f1xx_hal_uart.c" in mk,
        "module": module_enabled(conf, "HAL_UART_MODULE_ENABLED") or "HAL_UART_MODULE_ENABLED" in conf,
    }
    if mode in {"interrupt", "it"}:
        checks["irq"] = "USART1_IRQHandler" in text or "USART2_IRQHandler" in text
        checks["it_api"] = "HAL_UART_Receive_IT" in text or "HAL_UART_Transmit_IT" in text
        checks["nvic"] = "HAL_NVIC_EnableIRQ" in text and "USART" in text
    if mode == "dma":
        checks["dma_clock"] = "__HAL_RCC_DMA1_CLK_ENABLE" in text
        checks["dma_api"] = "HAL_UART_Receive_DMA" in text or "HAL_UART_Transmit_DMA" in text
        checks["dma_irq"] = "DMA1_Channel5_IRQHandler" in text or "DMA1_Channel4_IRQHandler" in text
        checks["usart_irq"] = "USART1_IRQHandler" in text
    out = result_from_checks(checks)
    out["task"] = "usart"
    out["mode"] = mode
    return out
