import type { CodeFile, FileNode } from "@/types/debug";

export const fileTree: FileNode[] = [
  {
    name: "STM32_LED_Project",
    path: "/",
    type: "folder",
    children: [
      {
        name: "Core",
        path: "/Core",
        type: "folder",
        children: [
          {
            name: "Inc",
            path: "/Core/Inc",
            type: "folder",
            children: [
              { name: "main.h", path: "/Core/Inc/main.h", type: "file" },
              { name: "gpio.h", path: "/Core/Inc/gpio.h", type: "file" },
              { name: "stm32f1xx_it.h", path: "/Core/Inc/stm32f1xx_it.h", type: "file" },
            ],
          },
          {
            name: "Src",
            path: "/Core/Src",
            type: "folder",
            children: [
              { name: "main.c", path: "/Core/Src/main.c", type: "file" },
              { name: "gpio.c", path: "/Core/Src/gpio.c", type: "file" },
              { name: "stm32f1xx_it.c", path: "/Core/Src/stm32f1xx_it.c", type: "file" },
            ],
          },
        ],
      },
      { name: "Drivers", path: "/Drivers", type: "folder", children: [] },
      { name: "CMSIS", path: "/CMSIS", type: "folder", children: [] },
      { name: "Makefile", path: "/Makefile", type: "file" },
      { name: "README.md", path: "/README.md", type: "file" },
    ],
  },
];

export const MAIN_C_BROKEN = `/* USER CODE BEGIN Header */
/**
  * @file           : main.c
  * @brief          : STM32F103C8T6 LED blink on PA5
  */
/* USER CODE END Header */
#include "main.h"
#include "gpio.h"

void SystemClock_Config(void);

int main(void)
{
  HAL_Init();
  SystemClock_Config();
  MX_GPIO_Init();

  while (1)
  {
    HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_5);
    HAL_Delay(500);
  }
}

void SystemClock_Config(void)
{
  RCC_OscInitTypeDef osc = {0};
  RCC_ClkInitTypeDef clk = {0};

  osc.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  osc.HSEState = RCC_HSE_ON;
  osc.PLL.PLLState = RCC_PLL_ON;
  osc.PLL.PLLSource = RCC_PLLSOURCE_HSE;
  osc.PLL.PLLMUL = RCC_PLL_MUL9;
  HAL_RCC_OscConfig(&osc);

  clk.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK
                | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
  clk.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  clk.AHBCLKDivider = RCC_SYSCLK_DIV1;
  clk.APB1CLKDivider = RCC_HCLK_DIV2;
  clk.APB2CLKDivider = RCC_HCLK_DIV1;
  HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_2);
}
`;

export const MAIN_H = `#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

#include "stm32f1xx_hal.h"

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
`;

export const GPIO_H_BROKEN = `#ifndef __GPIO_H
#define __GPIO_H

#ifdef __cplusplus
extern "C" {
#endif

void MX_GPIO_Init(void);

#ifdef __cplusplus
}
#endif

#endif /* __GPIO_H */
`;

export const GPIO_H_FIXED = `#ifndef __GPIO_H
#define __GPIO_H

#ifdef __cplusplus
extern "C" {
#endif

#include "stm32f1xx_hal.h"

#define LED_Pin       GPIO_PIN_5
#define LED_GPIO_Port GPIOA

void MX_GPIO_Init(void);

#ifdef __cplusplus
}
#endif

#endif /* __GPIO_H */
`;

export const GPIO_C = `#include "gpio.h"

void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef gpio = {0};

  __HAL_RCC_GPIOA_CLK_ENABLE();

  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_RESET);

  gpio.Pin = GPIO_PIN_5;
  gpio.Mode = GPIO_MODE_OUTPUT_PP;
  gpio.Pull = GPIO_NOPULL;
  gpio.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOA, &gpio);
}
`;

export const MAKEFILE = `TARGET = stm32_led
MCU = cortex-m3
CC = arm-none-eabi-gcc
CFLAGS = -mcpu=$(MCU) -mthumb -O2 -Wall
LDFLAGS = -T STM32F103C8Tx_FLASH.ld -Wl,--gc-sections

SRCS = Core/Src/main.c Core/Src/gpio.c Core/Src/stm32f1xx_it.c
OBJS = $(SRCS:.c=.o)

all: $(TARGET).elf $(TARGET).hex $(TARGET).bin

$(TARGET).elf: $(OBJS)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^

%.hex: %.elf
	arm-none-eabi-objcopy -O ihex $< $@

%.bin: %.elf
	arm-none-eabi-objcopy -O binary $< $@
`;

export const README = `# STM32_LED_Project

STM32F103C8T6，PA5 控制 LED，每 500ms 翻转一次。

- Framework: HAL
- Toolchain: ARM GCC 13.2
- Clock: 72 MHz (HSE + PLL)
`;

export const IT_C = `#include "stm32f1xx_it.h"
#include "main.h"

void SysTick_Handler(void)
{
  HAL_IncTick();
}

void NMI_Handler(void) { while (1) {} }
void HardFault_Handler(void) { while (1) {} }
`;

export const IT_H = `#ifndef __STM32F1XX_IT_H
#define __STM32F1XX_IT_H
void NMI_Handler(void);
void HardFault_Handler(void);
void SysTick_Handler(void);
#endif
`;

export const initialFiles: Record<string, CodeFile> = {
  "/Core/Src/main.c": { path: "/Core/Src/main.c", language: "c", content: MAIN_C_BROKEN },
  "/Core/Inc/main.h": { path: "/Core/Inc/main.h", language: "c", content: MAIN_H },
  "/Core/Inc/gpio.h": { path: "/Core/Inc/gpio.h", language: "c", content: GPIO_H_BROKEN },
  "/Core/Src/gpio.c": { path: "/Core/Src/gpio.c", language: "c", content: GPIO_C },
  "/Core/Src/stm32f1xx_it.c": { path: "/Core/Src/stm32f1xx_it.c", language: "c", content: IT_C },
  "/Core/Inc/stm32f1xx_it.h": { path: "/Core/Inc/stm32f1xx_it.h", language: "c", content: IT_H },
  "/Makefile": { path: "/Makefile", language: "makefile", content: MAKEFILE },
  "/README.md": { path: "/README.md", language: "markdown", content: README },
};
