---
name: stm32-adc
description: STM32F103 ADC polling or DMA. PASS requires CEA:ADC:value=0..4095.
---

# STM32 ADC

## When
Potentiometer, analog read, ADC DMA.

## Preconditions
inspect + pin conflicts. Default ADC1_IN0 on PA0 — conflicts with TIM2_CH1 / EXTI0.

## Tool order
inspect_project → parse_ioc → check_pin_conflicts → configure_peripheral kind=adc → build_project → diagnose_build → flash_firmware → read_serial → validate_hardware task=adc

## Forbidden
- Forcing ADC onto a pin already used by PWM/EXTI without explaining the conflict.
- PASS when `CEA:ADC:value=` is missing or out of 0–4095.

## Verify
Serial token `CEA:ADC:value=N` with N in 0..4095.

## Common errors
undefined `HAL_ADC_Init` / `HAL_ADC_Start_DMA`. PA0 occupancy.

## Failure
No serial → UNAVAILABLE/UNKNOWN, not PASS.

## Done
Build SUCCESS; hardware status matches evidence.
