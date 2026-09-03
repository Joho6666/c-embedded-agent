#ifndef ADC_H
#define ADC_H
#ifdef __cplusplus
extern "C" {
#endif
#include "main.h"
extern ADC_HandleTypeDef hadc1;
extern DMA_HandleTypeDef hdma_adc1;
void MX_ADC1_Init(void);
#ifdef __cplusplus
}
#endif
#endif
