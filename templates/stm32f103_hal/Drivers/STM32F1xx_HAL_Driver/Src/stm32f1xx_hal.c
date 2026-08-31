#include "stm32f1xx_hal.h"

static volatile uint32_t uwTick;

void SystemInit(void) {}

void HAL_Init(void)
{
  SysTick->LOAD = 8000U - 1U;
  SysTick->VAL = 0;
  SysTick->CTRL = 7U;
}

void HAL_IncTick(void) { uwTick++; }
uint32_t HAL_GetTick(void) { return uwTick; }

void HAL_Delay(uint32_t Delay)
{
  uint32_t start = uwTick;
  while ((uwTick - start) < Delay) {}
}

void HAL_GPIO_Init(GPIO_TypeDef *GPIOx, GPIO_InitTypeDef *GPIO_Init)
{
  uint32_t pin = GPIO_Init->Pin;
  for (uint32_t i = 0; i < 16; i++) {
    if ((pin & (1UL << i)) == 0) continue;
    if (i < 8) {
      uint32_t shift = i * 4;
      GPIOx->CRL = (GPIOx->CRL & ~(0xFUL << shift)) | (0x1UL << shift);
    } else {
      uint32_t shift = (i - 8) * 4;
      GPIOx->CRH = (GPIOx->CRH & ~(0xFUL << shift)) | (0x1UL << shift);
    }
  }
}

void HAL_GPIO_WritePin(GPIO_TypeDef *GPIOx, uint16_t GPIO_Pin, int PinState)
{
  if (PinState) GPIOx->BSRR = GPIO_Pin;
  else GPIOx->BRR = GPIO_Pin;
}

void HAL_GPIO_TogglePin(GPIO_TypeDef *GPIOx, uint16_t GPIO_Pin)
{
  GPIOx->ODR ^= GPIO_Pin;
}
