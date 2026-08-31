#include "main.h"
#include "gpio.h"

int main(void)
{
  HAL_Init();
  MX_GPIO_Init();
  while (1)
  {
    HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_5);
    HAL_Delay(500);
  }
}
