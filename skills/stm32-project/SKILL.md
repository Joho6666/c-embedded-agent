---
name: stm32-project
description: Inspect and understand an STM32F103 HAL project before changing code.
---

# STM32 Project

## When
Opening an unknown STM32 tree, importing CubeMX, or before any GPIO/USART/build work.

## Preconditions
- Project root is a real directory.
- Do not assume ESP32 / C51 / RP2040. Production target is STM32F103 only.

## Tool order
1. `inspect_project`
2. `parse_ioc` if `.ioc` exists
3. `get_board_context`
4. `check_pin_conflicts`

## Forbidden
- Recreating the whole project because inspect looks incomplete.
- Editing `Drivers/`, `startup*`, `*.ld`, `Makefile`, `*.ioc` unless a protected-file advanced path already exists.
- Inventing MCU, clocks, or pins when the tool returns null/unknown.

## Verify
Inspect returns platform STM32, MCU source `ioc` or clearly `defaulted`. Conflicts are not FAIL.

## Common errors
- No Makefile → cannot `build_project`.
- No `.ioc` → MCU may be defaulted STM32F103C8T6; treat as default, not measured.

## Failure
If inspect `FAIL`, stop. Fix the path. Do not flash.

## Done
You can name MCU, board, build system, toolchain availability, and IOC presence with evidence.
