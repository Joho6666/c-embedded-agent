---
name: stm32-spi
description: STM32F103 SPI1 on PA5/PA6/PA7.
---

# STM32 SPI

## When
SPI master, flash, display.

## Preconditions
SPI1 SCK/MISO/MOSI = PA5/PA6/PA7. NSS often PA4.

## Tool order
inspect_project → check_pin_conflicts → configure_peripheral kind=spi → build_project → diagnose_build → flash_firmware → validate_hardware

## Forbidden
- Reusing SWD pins.
- Fake PASS.

## Verify
Build SUCCESS. Hardware follows evidence only.

## Common errors
undefined `HAL_SPI_Init`. Pin overlap with TIM3 on PA6/PA7.

## Failure
Keep Drivers intact. Limited Error Memory retries.

## Done
SPI configuration builds; hardware not claimed without proof.
