from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.tools.filesystem import read_file, write_file

MODULES: dict[str, dict[str, Any]] = {
    "GPIO": {
        "macro": "HAL_GPIO_MODULE_ENABLED",
        "sources": ["Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_gpio.c"],
    },
    "UART": {
        "macro": "HAL_UART_MODULE_ENABLED",
        "sources": ["Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_uart.c"],
    },
    "USART": {
        "macro": "HAL_USART_MODULE_ENABLED",
        "sources": ["Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_usart.c"],
    },
    "TIM": {
        "macro": "HAL_TIM_MODULE_ENABLED",
        "sources": [
            "Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_tim.c",
            "Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_tim_ex.c",
        ],
    },
    "ADC": {
        "macro": "HAL_ADC_MODULE_ENABLED",
        "sources": [
            "Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_adc.c",
            "Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_adc_ex.c",
        ],
    },
    "DMA": {
        "macro": "HAL_DMA_MODULE_ENABLED",
        "sources": ["Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_dma.c"],
    },
    "I2C": {
        "macro": "HAL_I2C_MODULE_ENABLED",
        "sources": ["Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_i2c.c"],
    },
    "SPI": {
        "macro": "HAL_SPI_MODULE_ENABLED",
        "sources": ["Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_spi.c"],
    },
    "EXTI": {
        "macro": "HAL_EXTI_MODULE_ENABLED",
        "sources": ["Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_exti.c"],
    },
    "RCC": {
        "macro": "HAL_RCC_MODULE_ENABLED",
        "sources": [
            "Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_rcc.c",
            "Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_rcc_ex.c",
        ],
    },
}

_ALIASES = {
    "UART": "UART",
    "USART": "UART",
    "HAL_UART": "UART",
    "HAL_USART": "UART",
    "TIM": "TIM",
    "PWM": "TIM",
    "ADC": "ADC",
    "DMA": "DMA",
    "I2C": "I2C",
    "SPI": "SPI",
    "GPIO": "GPIO",
    "EXTI": "EXTI",
    "RCC": "RCC",
}


def normalize_module(name: str) -> str | None:
    key = (name or "").strip().upper().replace("HAL_", "").split()[0]
    key = key.replace("_MODULE_ENABLED", "").replace("_MODULE", "")
    return _ALIASES.get(key) or (key if key in MODULES else None)


def register_hal_module(root: Path, module: str) -> dict[str, Any]:
    """Enable HAL_*_MODULE_ENABLED and add HAL sources to Makefile without duplicates."""
    kind = normalize_module(module)
    if not kind:
        return {"ok": False, "reason": f"unknown module {module}", "files": []}
    spec = MODULES[kind]
    changed: list[str] = []
    notes: list[str] = []

    try:
        mk = read_file(root, "Makefile")
    except FileNotFoundError:
        return {"ok": False, "reason": "Makefile not found", "files": []}
    mk2 = mk
    for src in spec["sources"]:
        mk2, added = _ensure_c_source(mk2, src)
        if added:
            notes.append(f"added {src}")
        else:
            notes.append(f"already listed {src}")
    if mk2 != mk:
        write_file(root, "Makefile", mk2, advanced=True)
        changed.append("Makefile")

    conf_rel = "Core/Inc/stm32f1xx_hal_conf.h"
    try:
        conf = read_file(root, conf_rel)
    except FileNotFoundError:
        conf = None
        notes.append("hal_conf.h not found")
    if conf is not None:
        conf2 = _enable_hal_module(conf, spec["macro"])
        if conf2 != conf:
            write_file(root, conf_rel, conf2, advanced=True)
            changed.append(conf_rel)
            notes.append(f"enabled {spec['macro']}")
        else:
            notes.append(f"{spec['macro']} already enabled")

    return {
        "ok": True,
        "module": kind,
        "applied": bool(changed),
        "files": changed,
        "notes": notes,
        "sources": spec["sources"],
        "macro": spec["macro"],
    }


def _ensure_c_source(makefile: str, rel: str) -> tuple[str, bool]:
    if rel in makefile:
        return makefile, False
    lines = makefile.splitlines(keepends=True)
    last_src = -1
    for i, line in enumerate(lines):
        if "Drivers/STM32F1xx_HAL_Driver/Src/" in line or line.strip().endswith(".c \\"):
            last_src = i
    if last_src < 0:
        return makefile, False
    insert = f"\t{rel} \\\n"
    prev = lines[last_src]
    if not prev.rstrip("\n").endswith("\\"):
        lines[last_src] = prev.rstrip("\n") + " \\\n"
        lines.insert(last_src + 1, insert.rstrip(" \\\n") + "\n")
    else:
        lines.insert(last_src + 1, insert)
    return "".join(lines), True


def _enable_hal_module(conf: str, macro: str) -> str:
    define = f"#define {macro}"
    if re.search(rf"^\s*{re.escape(define)}\s*$", conf, re.M):
        return conf
    commented = [
        (rf"/\*\s*{re.escape(define)}\s*\*/", define),
        (rf"//\s*{re.escape(define)}", define),
    ]
    for pat, repl in commented:
        if re.search(pat, conf):
            return re.sub(pat, repl, conf, count=1)
    m = None
    for m in re.finditer(r"^#define HAL_[A-Z0-9_]+_MODULE_ENABLED\s*$", conf, re.M):
        pass
    if m:
        idx = m.end()
        return conf[:idx] + "\n" + define + conf[idx:]
    return conf + f"\n{define}\n"
