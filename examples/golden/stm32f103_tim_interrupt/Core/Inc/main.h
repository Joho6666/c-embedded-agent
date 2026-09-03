#ifndef MAIN_H
#define MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

#include "stm32f1xx_hal.h"

void Error_Handler(void);
void assert_failed(uint8_t *file, uint32_t line);

#define LED_GPIO_Port GPIOC
#define LED_Pin GPIO_PIN_13

#ifdef __cplusplus
}
#endif
#endif
