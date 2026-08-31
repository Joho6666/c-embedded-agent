---
title: USART
source: RM0008
page: 787
section: USART
mcu: STM32F103
type: reference_manual
---

# USART1 (RM0008)

默认引脚：PA9 = USART1_TX，PA10 = USART1_RX。

步骤：

1. `__HAL_RCC_USART1_CLK_ENABLE();` `__HAL_RCC_GPIOA_CLK_ENABLE();`
2. PA9 AF_PP，PA10 INPUT（或 AF_INPUT，Cube HAL 常用 GPIO_MODE_AF_PP / GPIO_MODE_INPUT）
3. `huart.Instance = USART1; huart.Init.BaudRate = 115200; WordLength 8; StopBits 1; Parity NONE; Mode TX_RX`
4. `HAL_UART_Init(&huart);`
5. `HAL_UART_Transmit(&huart, buf, len, HAL_MAX_DELAY);`

DMA 接收用 USART1_RX -> DMA1 Channel 5（RM0008 DMA mapping）。
