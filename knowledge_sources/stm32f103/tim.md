---
title: TIM
source: RM0008
page: 365
section: TIM
mcu: STM32F103
type: reference_manual
---

# TIM / PWM

TIM2 CH1 默认 PA0。TIM2 在 APB1。

PWM：`HAL_TIM_PWM_Init` + `HAL_TIM_PWM_ConfigChannel` + `HAL_TIM_PWM_Start`。GPIO 设为 AF_PP。F1 的 AF 没有现代 MCU 的 AFR 寄存器，通过 GPIOx CRL/CRH 的 CNF=0b10 选择复用推挽。
