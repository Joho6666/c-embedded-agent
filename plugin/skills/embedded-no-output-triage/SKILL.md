---
name: embedded-no-output-triage
description: Systematic triage when STM32 firmware builds and flashes but "nothing happens" — no serial output, LED stuck, board seems hung. Use on "没反应", "串口没输出", "LED 不闪", "卡死", "hang", "no output".
---

# "It flashed but nothing happens"

Work from the board's actual state, one layer at a time. Use the `cea-embedded` tools; do not
guess from the source alone.

1. **Is the right firmware on the board?** `status` → `last_flash.success`, `sha256_12`,
   `last_build.memory`. A failed or skipped flash means you are looking at old firmware.
2. **Is it running at all?** `read_pins(["PC13"])` twice with a pause, or
   `verify_behavior(led=[...])` if the code blinks. A frozen LED plus no output usually means it
   is stuck before the main loop:
   - clock init waiting on a ready flag (HSE missing / wrong `HSEState`),
   - `Error_Handler()` from a failed `HAL_*_Init` (check return values),
   - a HardFault or an IRQ falling into `Default_Handler` (handler name typo).
3. **Is the UART configured?** Pins (PA9 AF push-pull for USART1), peripheral clock, baud,
   `HAL_UART_Init` return value, the `huart` instance actually used by `_write`.
4. **Is output buffered?** printf without `\r\n` or without `setvbuf(stdout, NULL, _IONBF, 0)`
   may never flush.
5. **Wrong channel?** The code may print on USART2 while you read USART1 — `serial_read`
   returns the channel of every line.

Change one thing, `flash` again with an `expect`, and compare `status` before/after. Report which
layer the fault was in and the evidence kind (`SIMULATED` / `HARDWARE`).
