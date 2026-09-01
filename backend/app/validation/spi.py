from __future__ import annotations

from pathlib import Path
from typing import Any

from app.validation.base import core_source_text, module_enabled, read_hal_conf, read_makefile, result_from_checks


def validate_spi(root: Path) -> dict[str, Any]:
    text = core_source_text(root)
    mk = read_makefile(root)
    conf = read_hal_conf(root)
    checks = {
        "spi_clock": "__HAL_RCC_SPI1_CLK_ENABLE" in text or "__HAL_RCC_SPI2_CLK_ENABLE" in text,
        "gpio_clock": "__HAL_RCC_GPIOA_CLK_ENABLE" in text or "__HAL_RCC_GPIOB_CLK_ENABLE" in text,
        "hal_init": "HAL_SPI_Init" in text,
        "msp": "HAL_SPI_MspInit" in text,
        "api": "HAL_SPI_Transmit" in text or "HAL_SPI_TransmitReceive" in text,
        "source": "stm32f1xx_hal_spi.c" in mk,
        "module": module_enabled(conf, "HAL_SPI_MODULE_ENABLED") or "HAL_SPI_MODULE_ENABLED" in conf,
    }
    out = result_from_checks(checks)
    out["task"] = "spi"
    return out
