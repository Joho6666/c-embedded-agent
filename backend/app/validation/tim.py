from __future__ import annotations

from pathlib import Path
from typing import Any

from app.validation.base import core_source_text, module_enabled, read_hal_conf, read_makefile, result_from_checks


def validate_tim(root: Path, mode: str = "interrupt") -> dict[str, Any]:
    text = core_source_text(root)
    mk = read_makefile(root)
    conf = read_hal_conf(root)
    checks = {
        "tim_clock": "__HAL_RCC_TIM2_CLK_ENABLE" in text or "__HAL_RCC_TIM3_CLK_ENABLE" in text,
        "hal_init": "HAL_TIM_Base_Init" in text or "HAL_TIM_PWM_Init" in text,
        "prescaler": "Prescaler" in text,
        "period": "Period" in text,
        "source": "stm32f1xx_hal_tim.c" in mk,
        "module": module_enabled(conf, "HAL_TIM_MODULE_ENABLED") or "HAL_TIM_MODULE_ENABLED" in conf,
    }
    if mode == "interrupt":
        checks["irq_handler"] = "TIM2_IRQHandler" in text or "TIM3_IRQHandler" in text
        checks["nvic"] = "HAL_NVIC_EnableIRQ" in text and "TIM" in text
        checks["start_it"] = "HAL_TIM_Base_Start_IT" in text
    out = result_from_checks(checks)
    out["task"] = "tim"
    return out
