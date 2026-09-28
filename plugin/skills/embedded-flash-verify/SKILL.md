---
name: embedded-flash-verify
description: Use whenever you change STM32 firmware code (Makefile + arm-none-eabi-gcc projects) and need to know it actually works — build, one-click flash to the board or virtual board, read serial/pins, and assert timing. Trigger on "烧录", "flash", "跑一下看看", "验证固件", "LED 不闪", "串口没输出", or after any edit to Core/Src or Core/Inc.
---

# Embedded flash & verify loop

Compiling is not done. Firmware is done when the board **does** what was asked, and you can
point at the evidence. The `cea-embedded` MCP server gives you the board.

## Loop

1. **Edit** only application code (`Core/Src`, `Core/Inc`). Leave `Drivers/`, startup files and
   the linker script alone unless the task is about them.
2. **`flash`** with an `expect` string the firmware prints at boot:
   `flash(project=<dir>, expect="CEA:BOOT OK", observe_seconds=2)`.
   - `stage: "build"` → fix the reported `errors` (file/line/message) and repeat.
   - `expect_found: false` → the firmware runs but did not print it: check UART init, pins,
     `_write`/printf redirection (see `stm32f1-bluepill-pitfalls`).
3. **`status`** to see the latest state: firmware hash on the board, last build size, recent
   serial lines, `PC13` level (`board_led_on` accounts for the active-low LED).
4. For **timing** (blink periods, "every N ms"), run
   `verify_behavior(led=[{"pin":"PC13","on_ms":200,"off_ms":800}])` — a fresh deterministic
   simulation with ±5 % tolerance. For output, `verify_behavior(uart=[{"peripheral":"usart1","expect":"..."}])`.
5. Only then report success, and **say which evidence** you have.

## Evidence rules

| `evidence` | Meaning | How to report |
|---|---|---|
| `HARDWARE` | Real probe + serial | "verified on the board" |
| `SIMULATED` | Virtual Blue Pill (Renode) | "verified in simulation; not yet on hardware" |
| `UNAVAILABLE` | Tool could not run | say so; never claim it works |

Never infer success from a clean build, from reading the code, or from a missing error.

## Tips

- Give boot banners unique, greppable text (`CEA:BOOT OK`), terminated with `\r\n`.
- `serial_read(since_seq=<last_seq>)` returns only new lines — use it to watch a running board.
- `serial_write("help\r\n")` drives a firmware console; follow with `serial_read`.
- `pin_check` before adding a peripheral: it lists pins already claimed and flags conflicts.
- Simulation time runs slower than wall time; judge timing with `verify_behavior`, not by
  sampling `read_pins` in a loop.
