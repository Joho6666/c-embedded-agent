---
title: GPIO
source: RM0008
page: 160
section: GPIO
mcu: STM32F103
type: reference_manual
---

# STM32F103 GPIO (RM0008)

GPIO 位于 APB2。每个端口有 CRL（pin0-7）和 CRH（pin8-15）。

输出前必须：

1. 使能对应端口时钟，例如 PC13：`__HAL_RCC_GPIOC_CLK_ENABLE();`
2. `GPIO_InitTypeDef`：`Pin`、`Mode = GPIO_MODE_OUTPUT_PP`、`Pull = GPIO_NOPULL`、`Speed`
3. `HAL_GPIO_Init(GPIOx, &gpio);`
4. 翻转：`HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_13);`
5. 延时：`HAL_Delay(500);`

Blue Pill 板载 LED 在 **PC13**（多数板子低电平点亮）。Nucleo 风格示例常用 PA5，不要默认当成 Blue Pill。

PA9 = USART1_TX，PA10 = USART1_RX（默认 AF 映射）。
