---
title: ADC
source: RM0008
page: 218
section: ADC
mcu: STM32F103
type: reference_manual
---

# ADC

ADC1 IN0 = PA0。轮询：`HAL_ADC_Start` + `HAL_ADC_PollForConversion` + `HAL_ADC_GetValue`。DMA：ADC1 -> DMA1 Channel 1。
