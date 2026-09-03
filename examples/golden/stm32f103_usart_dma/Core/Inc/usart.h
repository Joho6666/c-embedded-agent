#ifndef USART_H
#define USART_H
#ifdef __cplusplus
extern "C" {
#endif
#include "main.h"
extern UART_HandleTypeDef huart1;
extern DMA_HandleTypeDef hdma_usart1_rx;
void MX_USART1_UART_Init(void);
#ifdef __cplusplus
}
#endif
#endif
