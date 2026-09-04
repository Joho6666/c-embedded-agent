---
name: stm32-build-flash-validate
description: Real ARM GCC build, OpenOCD flash, serial, hardware validate. Never fake PASS.
---

# STM32 Build Flash Validate

## When
Need artifacts, a programmed board, or a hardware verdict.

## Preconditions
inspect_project toolchain fields. Missing gcc/make → UNAVAILABLE, do not invent Build Successful.

## Tool order
inspect_project → build_project → diagnose_build (if FAIL) → flash_firmware confirm=true → list_serial_ports → read_serial → validate_hardware confirm=true

## Forbidden
- Returning Build Successful without firmware.elf.
- Mock flash/serial.
- Hardware PASS without a board.
- confirm=false on flash/validate (tools refuse).

## Verify
| Layer | Honest status |
|---|---|
| Toolchain missing | UNAVAILABLE |
| make 0 but no ELF | FAIL |
| OpenOCD missing | UNAVAILABLE |
| No serial/probe | UNKNOWN / UNAVAILABLE / PARTIAL |
| USART token | PASS only with CEA:USART:PASS |

## Common errors
No ST-LINK, wrong MCU family, baud not 9600/115200.

## Failure
Stop flashing after Core rate limit. Report logs.

## Done
Artifacts listed; flash/validate status matches real tools.
