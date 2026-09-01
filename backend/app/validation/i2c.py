from __future__ import annotations

from pathlib import Path
from typing import Any

from app.validation.base import core_source_text, module_enabled, read_hal_conf, read_makefile, result_from_checks


def validate_i2c(root: Path) -> dict[str, Any]:
    text = core_source_text(root)
    mk = read_makefile(root)
    conf = read_hal_conf(root)
    checks = {
        "i2c_clock": "__HAL_RCC_I2C1_CLK_ENABLE" in text or "__HAL_RCC_I2C2_CLK_ENABLE" in text,
        "gpio_clock": "__HAL_RCC_GPIOB_CLK_ENABLE" in text,
        "hal_init": "HAL_I2C_Init" in text,
        "msp": "HAL_I2C_MspInit" in text,
        "api": "HAL_I2C_Master_Transmit" in text or "HAL_I2C_Master_Receive" in text or "HAL_I2C_IsDeviceReady" in text,
        "source": "stm32f1xx_hal_i2c.c" in mk,
        "module": module_enabled(conf, "HAL_I2C_MODULE_ENABLED") or "HAL_I2C_MODULE_ENABLED" in conf,
    }
    out = result_from_checks(checks)
    out["task"] = "i2c"
    return out
