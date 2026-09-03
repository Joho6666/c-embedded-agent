from __future__ import annotations

from pathlib import Path
from typing import Any

from app.validation.base import core_source_text, module_enabled, read_hal_conf, read_makefile, result_from_checks


def validate_adc(root: Path, mode: str = "polling") -> dict[str, Any]:
    text = core_source_text(root)
    mk = read_makefile(root)
    conf = read_hal_conf(root)
    checks = {
        "adc_clock": "__HAL_RCC_ADC1_CLK_ENABLE" in text,
        "gpio_analog": "GPIO_MODE_ANALOG" in text,
        "channel": "ADC_CHANNEL_" in text,
        "sample_time": "ADC_SAMPLETIME_" in text,
        "hal_init": "HAL_ADC_Init" in text,
        "config_channel": "HAL_ADC_ConfigChannel" in text,
        "source": "stm32f1xx_hal_adc.c" in mk,
        "module": module_enabled(conf, "HAL_ADC_MODULE_ENABLED") or "HAL_ADC_MODULE_ENABLED" in conf,
    }
    if mode == "dma":
        checks["dma"] = "HAL_ADC_Start_DMA" in text
        checks["dma_clock"] = "__HAL_RCC_DMA1_CLK_ENABLE" in text
    else:
        checks["start"] = "HAL_ADC_Start" in text or "HAL_ADC_PollForConversion" in text
    out = result_from_checks(checks)
    out["task"] = "adc"
    out["mode"] = mode
    return out
