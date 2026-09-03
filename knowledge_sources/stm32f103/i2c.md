---
title: I2C
source: RM0008
page: 755
section: I2C
mcu: STM32F103
type: reference_manual
---

# I2C1

默认 PB6 = SCL，PB7 = SDA，开漏 AF。使能 GPIOB 与 I2C1 时钟，调用 `HAL_I2C_Init`。
