---
title: HAL
source: STM32CubeF1
page: 1
section: HAL
mcu: STM32F103
type: cube
---

# STM32CubeF1 HAL

官方 HAL 头：`stm32f1xx_hal.h`。工程必须 `-DSTM32F103xB -DUSE_HAL_DRIVER`，并包含 `stm32f1xx_hal_conf.h`。

不要修改 `Drivers/`。用户代码放在 `Core/Src` 与 `Core/Inc`。

常用 API：

- `HAL_Init` / `HAL_Delay` / `HAL_GetTick`
- `HAL_GPIO_Init` / `HAL_GPIO_TogglePin`
- `HAL_UART_Init` / `HAL_UART_Transmit`
- `HAL_TIM_PWM_Init` / `HAL_TIM_PWM_Start`
- `HAL_ADC_Start` / `HAL_ADC_PollForConversion`
- `HAL_I2C_Master_Transmit`
- `HAL_SPI_TransmitReceive`

`GPIO_PIN_99` 之类不存在的宏是编译错误。`undefined reference to HAL_UART_Init` 是链接错误：未编译 `stm32f1xx_hal_uart.c`，或 `hal_conf.h` 未打开 `HAL_UART_MODULE_ENABLED`。
