#include "stm32f1xx_hal.h"
void SysTick_Handler(void) { HAL_IncTick(); }
void NMI_Handler(void) { while (1) {} }
void HardFault_Handler(void) { while (1) {} }
