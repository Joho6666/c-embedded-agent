# STM32 HAL 要点

- `HAL_Init()` 初始化 SysTick。
- `HAL_Delay(ms)` 依赖 SysTick_Handler 中的 `HAL_IncTick()`。
- GPIO 端口时钟在 APB2：`RCC_APB2ENR_IOPAEN`。
- 禁止编造不存在的 HAL API。不确定时查阅本知识库。
