---
name: stm32-usart
description: STM32F103 USART1 (PA9/PA10) polling, interrupt, or DMA.
---

# STM32 USART

## When
printf, UART loopback, interrupt receive, UART DMA.

## Preconditions
inspect + parse_ioc. Default USART1 TX PA9 RX PA10 115200.

## Tool order
inspect_project → parse_ioc → check_pin_conflicts → configure_peripheral kind=usart (or minimal edit) → build_project → diagnose_build → flash_firmware → read_serial expect=CEA:USART:PASS → validate_hardware task=usart

## Forbidden
- F4 `GPIO_AF7_USART1` on F1.
- Skipping HAL UART module in Makefile then claiming success.
- Fake serial logs.

## Verify
Hardware PASS only if serial contains `CEA:USART:PASS` (or the given expect). Empty serial is UNKNOWN/FAIL, never PASS.

## Common errors
undefined `HAL_UART_Init` → Error Memory `register_hal_module UART`. Missing IRQ handler for IT mode.

## Failure
Do not rebuild the project from the official template to hide USART errors. Max a few mechanical Error Memory fixes.

## Done
Build SUCCESS and, if hardware present, USART token observed.
