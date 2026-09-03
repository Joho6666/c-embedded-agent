from __future__ import annotations

from pathlib import Path
from typing import Any

from app.validation.base import core_source_text, module_enabled, read_hal_conf, read_makefile, result_from_checks


def validate_dma(root: Path) -> dict[str, Any]:
    text = core_source_text(root)
    mk = read_makefile(root)
    conf = read_hal_conf(root)
    checks = {
        "dma_clock": "__HAL_RCC_DMA1_CLK_ENABLE" in text,
        "hal_dma_init": "HAL_DMA_Init" in text,
        "link": "__HAL_LINKDMA" in text,
        "source": "stm32f1xx_hal_dma.c" in mk,
        "module": module_enabled(conf, "HAL_DMA_MODULE_ENABLED") or "HAL_DMA_MODULE_ENABLED" in conf,
        "irq": "DMA1_Channel" in text and "IRQHandler" in text,
    }
    out = result_from_checks(checks)
    out["task"] = "dma"
    return out
