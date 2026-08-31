#ifndef STM32F1XX_H
#define STM32F1XX_H
#include <stdint.h>

#define PERIPH_BASE        0x40000000UL
#define APB2PERIPH_BASE    (PERIPH_BASE + 0x00010000UL)
#define AHBPERIPH_BASE     (PERIPH_BASE + 0x00018000UL)
#define GPIOA_BASE         (APB2PERIPH_BASE + 0x0800UL)
#define RCC_BASE           (AHBPERIPH_BASE + 0x9000UL)
#define FLASH_R_BASE       0x40022000UL
#define SCS_BASE           0xE000E000UL
#define SysTick_BASE       (SCS_BASE + 0x0010UL)

typedef struct { volatile uint32_t CRL, CRH, IDR, ODR, BSRR, BRR, LCKR; } GPIO_TypeDef;
typedef struct { volatile uint32_t CR, CFGR, CIR, APB2RSTR, APB1RSTR, AHBENR, APB2ENR, APB1ENR, BDCR, CSR; } RCC_TypeDef;
typedef struct { volatile uint32_t CTRL, LOAD, VAL, CALIB; } SysTick_Type;

#define GPIOA   ((GPIO_TypeDef *) GPIOA_BASE)
#define RCC     ((RCC_TypeDef *) RCC_BASE)
#define SysTick ((SysTick_Type *) SysTick_BASE)

#define RCC_APB2ENR_IOPAEN (1UL << 2)
#endif
