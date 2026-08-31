---
title: Startup Linker
source: CMSIS Device F1
page: 1
section: Startup
mcu: STM32F103
type: cmsis
---

# Startup and linker

`startup_stm32f103xb.s` 设置向量表、复制 .data、清 .bss、调用 `SystemInit` 与 `main`。链接脚本 Flash 64K @ 0x08000000，RAM 20K @ 0x20000000。不要让 Agent 随意改 startup 或 `.ld`。
