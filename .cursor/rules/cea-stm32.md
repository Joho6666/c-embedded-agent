# CEA STM32 rules (Cursor)

- Production MCU is STM32F103 only. ESP32 / C51 / RP2040 are not supported.
- Use CEA MCP tools for inspect / IOC / build / diagnose / flash / serial / validate.
- Follow `skills/stm32-debugging/SKILL.md`.
- Do not edit Drivers/, startup*, *.ld, Makefile, *.ioc unless Error Memory mechanical HAL-module Makefile edits are required.
- Compile success is not hardware PASS.
- Never fake serial logs or flash success.
- Stop after a few failed flash/build loops.
