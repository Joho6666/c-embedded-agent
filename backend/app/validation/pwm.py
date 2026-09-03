from __future__ import annotations

from pathlib import Path
from typing import Any

from app.validation.base import core_source_text, module_enabled, read_hal_conf, read_makefile, result_from_checks


def validate_pwm(root: Path) -> dict[str, Any]:
    text = core_source_text(root)
    mk = read_makefile(root)
    conf = read_hal_conf(root)
    checks = {
        "tim_clock": "__HAL_RCC_TIM2_CLK_ENABLE" in text or "__HAL_RCC_TIM3_CLK_ENABLE" in text,
        "prescaler": "Prescaler" in text,
        "period": "Period" in text,
        "channel": "TIM_CHANNEL_" in text,
        "gpio_af": "GPIO_MODE_AF_PP" in text,
        "pwm_init": "HAL_TIM_PWM_Init" in text,
        "pwm_start": "HAL_TIM_PWM_Start" in text,
        "source": "stm32f1xx_hal_tim.c" in mk,
        "module": module_enabled(conf, "HAL_TIM_MODULE_ENABLED") or "HAL_TIM_MODULE_ENABLED" in conf,
    }
    out = result_from_checks(checks)
    out["task"] = "pwm"
    return out
