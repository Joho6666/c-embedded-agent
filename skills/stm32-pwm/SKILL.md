---
name: stm32-pwm
description: STM32F103 TIM PWM. Without a probe, status is PARTIAL not PASS.
---

# STM32 PWM

## When
Duty cycle, servo, TIM2 PWM on PA0.

## Preconditions
PA0 is TIM2_CH1 by default and collides with ADC1_IN0 / EXTI0.

## Tool order
inspect_project → check_pin_conflicts → configure_peripheral kind=pwm → build_project → diagnose_build → flash_firmware → validate_hardware task=pwm

## Forbidden
- Reporting hardware PASS without a measurement device.
- Disabling TIM to fix a linker error.

## Verify
Build SUCCESS. No probe → PARTIAL (`no measurement device`). Never PASS.

## Common errors
undefined `HAL_TIM_PWM_Init`. Pin occupancy on PA0.

## Failure
PARTIAL/UNAVAILABLE is an honest result. Stop looping flash.

## Done
Firmware builds; hardware status is PARTIAL or better with evidence.
