# Golden: STM32F103C8T6 Blue Pill LED

Board LED on **PC13**, toggle every 500ms.

This tree is a copy of `templates/stm32f103_hal_official` used as an Agent regression fixture.

```bash
make clean && make -j4
```

Produces `firmware.elf` / `firmware.hex` / `firmware.bin`.

To refresh from the official template:

```bash
python examples/golden/sync_led.py
```
