---
name: stm32-dma
description: STM32F103 DMA with USART or ADC. IRQ handlers must be real, not empty stubs as a goal.
---

# STM32 DMA

## When
USART DMA, ADC DMA.

## Preconditions
inspect + parse_ioc DMA channels. Enable HAL UART/ADC **and** DMA.

## Tool order
inspect_project → parse_ioc → build_project → diagnose_build (look for DMA IRQ / HAL_*_DMA undef) → minimal fix → build_project → flash_firmware → read_serial → validate_hardware

## Forbidden
- Empty IRQ stub as the finished solution (linker-green, runtime-wrong).
- Disabling DMA to make the link succeed.

## Verify
Symbols resolve. USART DMA still needs `CEA:USART:PASS`. ADC DMA needs `CEA:ADC:value=`.

## Common errors
`HAL_UART_Receive_DMA` / `HAL_ADC_Start_DMA` undef. `DMA1_ChannelN_IRQHandler` missing.

## Failure
Do not regenerate the tree. Apply Error Memory mechanical HAL+DMA register, then rebuild.

## Done
DMA path compiles; hardware evidence required for PASS.
