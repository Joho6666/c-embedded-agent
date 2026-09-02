#include "main.h"
#include "gpio.h"
#include "usart.h"

static void SystemClock_Config(void);
static uint8_t rx;

int main(void)
{
  HAL_Init();
  SystemClock_Config();
  MX_GPIO_Init();
  MX_USART1_UART_Init();
  HAL_UART_Receive_IT(&huart1, &rx, 1);
  while (1)
  {
  }
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
  if (huart->Instance == USART1)
  {
    HAL_UART_Transmit_IT(&huart1, &rx, 1);
    HAL_UART_Receive_IT(&huart1, &rx, 1);
  }
}

static void SystemClock_Config(void)
{
  RCC_OscInitTypeDef osc = {0};
  RCC_ClkInitTypeDef clk = {0};
  osc.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  osc.HSEState = RCC_HSE_ON;
  osc.HSEPredivValue = RCC_HSE_PREDIV_DIV1;
  osc.PLL.PLLState = RCC_PLL_ON;
  osc.PLL.PLLSource = RCC_PLLSOURCE_HSE;
  osc.PLL.PLLMUL = RCC_PLL_MUL9;
  if (HAL_RCC_OscConfig(&osc) != HAL_OK) { Error_Handler(); }
  clk.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
  clk.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  clk.AHBCLKDivider = RCC_SYSCLK_DIV1;
  clk.APB1CLKDivider = RCC_HCLK_DIV2;
  clk.APB2CLKDivider = RCC_HCLK_DIV1;
  if (HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_2) != HAL_OK) { Error_Handler(); }
}

void Error_Handler(void) { __disable_irq(); while (1) {} }
void assert_failed(uint8_t *file, uint32_t line) { (void)file; (void)line; }
