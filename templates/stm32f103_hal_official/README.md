# STM32F103C8T6 official HAL template

Blue Pill / STM32F103C8T6, STM32CubeF1 HAL (not a homemade stub).

- MCU: STM32F103C8T6 (Cortex-M3, 64KB Flash, 20KB RAM)
- Clock: 8MHz HSE, PLL x9 = 72MHz
- On-board LED: **PC13** (active low on most Blue Pill boards)
- Optional LED: redefine `LED_GPIO_Port` / `LED_Pin` to `GPIOA` / `GPIO_PIN_5`

## Build

```bash
make clean
make -j4
```

Produces `firmware.elf`, `firmware.hex`, `firmware.bin`.

Requires `arm-none-eabi-gcc`, `arm-none-eabi-objcopy`, `arm-none-eabi-size`, and `make`.

Drivers are vendored from STMicroelectronics STM32CubeF1 — see `THIRD_PARTY.md`. Refresh with:

```bash
python scripts/sync_cubef1.py
```
