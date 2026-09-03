---
title: NVIC
source: PM0056
page: 1
section: NVIC
mcu: STM32F103
type: programming_manual
---

# NVIC / Cortex-M3

`HAL_NVIC_SetPriority` + `HAL_NVIC_EnableIRQ`。SysTick 由 `HAL_Init` 配置 1ms tick。EXTI 线对应 GPIO 号：EXTI13 对应 PC13。
