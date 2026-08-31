---
title: RCC
source: RM0008
page: 99
section: RCC
mcu: STM32F103
type: reference_manual
---

# RCC / Clock (RM0008)

Blue Pill 常见 8 MHz HSE。PLL x9 得到 72 MHz SYSCLK。

APB1 最大 36 MHz，因此 72 MHz 时 APB1 必须 DIV2。APB2 可为 72 MHz。Flash latency 2 wait states at 72 MHz.

HAL：`HAL_RCC_OscConfig` + `HAL_RCC_ClockConfig(..., FLASH_LATENCY_2)`。

外设时钟：GPIO 在 APB2（IOPAEN/IOPBEN/IOPCEN）。USART1 在 APB2，USART2/3 在 APB1。TIM2/3/4 在 APB1，TIM1 在 APB2。
