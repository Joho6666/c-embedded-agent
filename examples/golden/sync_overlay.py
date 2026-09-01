#!/usr/bin/env python3
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "templates" / "stm32f103_hal_official"

GOLDENS: dict[str, list[str]] = {
    "usart": ["Core/Src/usart.c"],
    "pwm": ["Core/Src/tim.c"],
    "exti": [],
    "tim_interrupt": ["Core/Src/tim.c"],
    "usart_it": ["Core/Src/usart.c"],
    "usart_dma": ["Core/Src/usart.c"],
    "adc": ["Core/Src/adc.c", "Core/Src/usart.c"],
    "adc_dma": ["Core/Src/adc.c"],
    "i2c": ["Core/Src/i2c.c"],
    "spi": ["Core/Src/spi.c"],
}

NOTES = {
    "usart": "# Golden: USART1 115200 TX\n\nPA9 TX / PA10 RX. Loops Hello + PC13 toggle.\n",
    "pwm": "# Golden: TIM2 PWM\n\nTIM2 CH1 on PA0 (AF_PP). 1kHz 50% duty.\n",
    "exti": "# Golden: EXTI0 PA0 falling, toggle PC13\n",
    "tim_interrupt": "# Golden: TIM3 update IRQ toggle PC13\n",
    "usart_it": "# Golden: USART1 RX interrupt echo\n",
    "usart_dma": "# Golden: USART1 DMA RX circular + TX PASS token\n",
    "adc": "# Golden: ADC1 poll PA0, print CEA:ADC:value=\n",
    "adc_dma": "# Golden: ADC1 DMA continuous PA0\n",
    "i2c": "# Golden: I2C1 PB6/PB7 scan 0x08-0x77\n",
    "spi": "# Golden: SPI1 master transmit 0xA5\n",
}


def sync(name: str, extra_sources: list[str] | None = None) -> None:
    extra_sources = extra_sources if extra_sources is not None else GOLDENS.get(name, [])
    overlay = Path(__file__).resolve().parent / "overlays" / name
    dest = Path(__file__).resolve().parent / f"stm32f103_{name}"
    if not (SRC / "Drivers/CMSIS/Include/core_cm3.h").is_file():
        raise SystemExit("official template missing Drivers")
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(SRC, dest, ignore=shutil.ignore_patterns("*.elf", "*.hex", "*.bin", "*.o", "*.map", ".git"))
    if overlay.is_dir():
        for src_file in overlay.rglob("*"):
            if src_file.is_file():
                target = dest / src_file.relative_to(overlay)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, target)
    makefile = dest / "Makefile"
    text = makefile.read_text(encoding="utf-8")
    needle = "\tCore/Src/gpio.c \\\n"
    insert = needle + "".join(f"\t{s} \\\n" for s in extra_sources if s not in text)
    if needle in text and extra_sources:
        makefile.write_text(text.replace(needle, insert, 1), encoding="utf-8")
    (dest / "README.md").write_text(NOTES.get(name, f"# Golden stm32f103_{name}\n"), encoding="utf-8")
    print("synced", dest)


def sync_all() -> None:
    for name in GOLDENS:
        sync(name, GOLDENS[name])


if __name__ == "__main__":
    import sys

    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which == "all":
        sync_all()
    else:
        sync(which, GOLDENS.get(which, []))
