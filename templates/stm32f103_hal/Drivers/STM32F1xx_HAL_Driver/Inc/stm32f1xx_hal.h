#ifndef STM32F1XX_HAL_H
#define STM32F1XX_HAL_H
#include "stm32f1xx.h"

#define HAL_MAX_DELAY 0xFFFFFFFFU
#define GPIO_PIN_5    (1U << 5)
#define GPIO_PIN_RESET 0
#define GPIO_PIN_SET   1
#define GPIO_MODE_OUTPUT_PP 0x01
#define GPIO_NOPULL 0
#define GPIO_SPEED_FREQ_LOW 0

typedef struct {
  uint32_t Pin;
  uint32_t Mode;
  uint32_t Pull;
  uint32_t Speed;
} GPIO_InitTypeDef;

void HAL_Init(void);
void HAL_IncTick(void);
void HAL_Delay(uint32_t Delay);
uint32_t HAL_GetTick(void);
void HAL_GPIO_Init(GPIO_TypeDef *GPIOx, GPIO_InitTypeDef *GPIO_Init);
void HAL_GPIO_WritePin(GPIO_TypeDef *GPIOx, uint16_t GPIO_Pin, int PinState);
void HAL_GPIO_TogglePin(GPIO_TypeDef *GPIOx, uint16_t GPIO_Pin);
void SystemInit(void);

#define __HAL_RCC_GPIOA_CLK_ENABLE() (RCC->APB2ENR |= RCC_APB2ENR_IOPAEN)
#endif
