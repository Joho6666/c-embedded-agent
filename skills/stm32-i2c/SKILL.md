---
name: stm32-i2c
description: STM32F103 I2C1 on PB6/PB7.
---

# STM32 I2C

## When
EEPROM, sensor, I2C1.

## Preconditions
Default SCL PB6 SDA PB7. Check occupancy before configure.

## Tool order
inspect_project → parse_ioc → check_pin_conflicts → configure_peripheral kind=i2c → build_project → diagnose_build → flash_firmware → validate_hardware

## Forbidden
- Editing Drivers HAL I2C sources.
- PASS without bus evidence.

## Verify
Build SUCCESS. Hardware PASS only with a defined expect token if one exists; otherwise UNKNOWN.

## Common errors
undefined `HAL_I2C_Init`. Missing pull-ups are hardware, not a reason to rewrite HAL.

## Failure
No device on the bus → FAIL/UNKNOWN, not a full project regenerate.

## Done
I2C init compiles; hardware status is honest.
