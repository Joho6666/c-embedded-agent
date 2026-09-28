---
name: stm32f1-bluepill-pitfalls
description: Known traps when writing STM32F103 / Blue Pill firmware with STM32CubeF1 HAL — LED polarity, printf redirection, UART pin setup, clock/flash latency, SWD pins, HAL_Delay semantics. Use when writing or debugging STM32F1 code, especially when output or timing is wrong but the code compiles.
---

# STM32F103 (Blue Pill) pitfalls

Each item compiles cleanly and fails at runtime. Check them before blaming the logic.

## Board

- **PC13 LED is active-low.** LED on = `GPIO_PIN_RESET`, off = `GPIO_PIN_SET`. "亮 200ms、灭 800ms"
  means 200 ms low then 800 ms high. Asymmetric blink specs are where this bites.
- **PC13–PC15 are weak outputs** (≤3 mA, 2 MHz). Fine for the LED, not for driving loads.
- **PA13/PA14 are SWD.** Never reconfigure them or you lose the debugger. `__HAL_AFIO_REMAP_SWJ_NOJTAG()`
  frees PA15/PB3/PB4 but keeps SWD.

## UART / printf

- **USART1 = PA9 (TX, `GPIO_MODE_AF_PP`) / PA10 (RX, input).** Enable both `__HAL_RCC_USART1_CLK_ENABLE()`
  and `__HAL_RCC_GPIOA_CLK_ENABLE()`. USART2 = PA2/PA3 on APB1.
- **printf needs `_write`.** If the project already has `syscalls.c` with a stub `_write`,
  defining another `_write` in `main.c` is a duplicate symbol — edit the one in `syscalls.c` to
  call `HAL_UART_Transmit`, and include `main.h` there for `UART_HandleTypeDef`.
- newlib buffers `stdout`: end lines with `\r\n`, or call `setvbuf(stdout, NULL, _IONBF, 0)`
  once, otherwise output appears late or not at all.
- `%f` in printf needs `-u _printf_float` in LDFLAGS with newlib-nano.

## Clocks

- 72 MHz = HSE 8 MHz × PLL9, **APB1 ≤ 36 MHz** (`RCC_HCLK_DIV2`), **FLASH_LATENCY_2**. Wrong
  latency → random HardFaults at speed.
- Timers on APB1 get ×2 when the APB1 prescaler ≠ 1: TIM2–TIM4 clock is 72 MHz, not 36 MHz.
- `HAL_Delay(n)` waits at least n ms (+1 tick). For periodic work use `HAL_GetTick()`
  differences (`now - last >= period`, then `last += period`) so timing does not drift.

## Interrupts

- An IRQ handler name typo (`USART1_IRQHandle`) silently falls into `Default_Handler`
  (infinite loop). Names must match the vector table in `startup_stm32f103xb.s`.
- Enable both the peripheral interrupt and `HAL_NVIC_EnableIRQ(...)`; call the HAL handler
  (`HAL_UART_IRQHandler(&huart1)`) from the IRQ, and do the work in the callback.
- Variables shared with an ISR must be `volatile`; multi-byte shared state needs a critical
  section (`__disable_irq()` / `__enable_irq()`).

## Verify

After fixing any of these, re-run `flash` with an `expect` string and, for timing,
`verify_behavior` (see `embedded-flash-verify`).
