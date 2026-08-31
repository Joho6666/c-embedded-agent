# STM32F103 GPIO (HAL)

PA5 属于 GPIOA。输出前必须：

1. `__HAL_RCC_GPIOA_CLK_ENABLE();`
2. `GPIO_InitTypeDef` 设置 `Pin = GPIO_PIN_5`, `Mode = GPIO_MODE_OUTPUT_PP`
3. `HAL_GPIO_Init(GPIOA, &gpio);`
4. 翻转：`HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_5);`
5. 延时：`HAL_Delay(500);` 得到约 500ms 半周期，整周期约 1000ms。

头文件：`stm32f1xx_hal.h` 定义 `GPIO_PIN_5`。gpio.c / gpio.h 必须 include 该头文件，否则会出现 `GPIO_PIN_5 undeclared`。
