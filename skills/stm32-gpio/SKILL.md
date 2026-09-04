---
name: stm32-gpio
description: STM32F103 GPIO / LED work on Blue Pill (PC13 active-low).
---

# STM32 GPIO

## When
LED blink, GPIO output/input, EXTI button.

## Preconditions
`inspect_project` then `get_board_context`. Default LED is PC13 unless IOC says otherwise.

## Tool order
inspect_project → parse_ioc → get_board_context → check_pin_conflicts → (minimal Core/Src edit) → build_project → diagnose_build

Hardware: flash_firmware → read_serial → validate_hardware. LED without probe is UNKNOWN, not PASS.

## Forbidden
- Using PA13/PA14 (SWD).
- Treating compile success as hardware PASS.
- Disabling EXTI/GPIO to silence a linker error.

## Verify
Static: pin init + toggle. Hardware: only PASS with real evidence; otherwise UNKNOWN / UNAVAILABLE.

## Common errors
PC13 active-low on Blue Pill. CubeMX GPIO vs AF conflict on the same pin.

## Failure
Pin FAIL → do not force unless the user explicitly accepts the conflict. Rebuild at most a few times with Error Memory fixes.

## Done
Requested GPIO behaves; build SUCCESS; hardware status is honest.
