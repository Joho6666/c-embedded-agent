#ifndef MAIN_H
#define MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

#include "stm32f1xx_hal.h"

void Error_Handler(void);

#define LED_GPIO_Port GPIOC
#define LED_Pin GPIO_PIN_13

#ifdef __cplusplus
}
#endif
#endif
