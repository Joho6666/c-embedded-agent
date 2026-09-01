#!/usr/bin/env python3
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "templates" / "stm32f103_hal_official"


def sync(name: str, extra_sources: list[str]) -> None:
    overlay = Path(__file__).resolve().parent / "overlays" / name
    dest = Path(__file__).resolve().parent / f"stm32f103_{name}"
    if not (SRC / "Drivers/CMSIS/Include/core_cm3.h").is_file():
        raise SystemExit("official template missing Drivers")
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(SRC, dest, ignore=shutil.ignore_patterns("*.elf", "*.hex", "*.bin", "*.o", "*.map", ".git"))
    for src_file in overlay.rglob("*"):
        if src_file.is_file():
            target = dest / src_file.relative_to(overlay)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, target)
    makefile = dest / "Makefile"
    text = makefile.read_text(encoding="utf-8")
    needle = "\tCore/Src/gpio.c \\\n"
    insert = needle + "".join(f"\t{s} \\\n" for s in extra_sources)
    if needle in text and extra_sources[0] not in text:
        makefile.write_text(text.replace(needle, insert, 1), encoding="utf-8")
    notes = {
        "usart": "# Golden: USART1 115200 TX\n\nPA9 TX / PA10 RX. Loops Hello + PC13 toggle.\n",
        "pwm": "# Golden: TIM2 PWM\n\nTIM2 CH1 on PA0 (AF_PP). 1kHz 50% duty. PC13 still toggles.\n",
    }
    (dest / "README.md").write_text(notes.get(name, f"# Golden stm32f103_{name}\n"), encoding="utf-8")
    print("synced", dest)


if __name__ == "__main__":
    import sys

    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in {"usart", "all"}:
        sync("usart", ["Core/Src/usart.c"])
    if which in {"pwm", "all"}:
        sync("pwm", ["Core/Src/tim.c"])
