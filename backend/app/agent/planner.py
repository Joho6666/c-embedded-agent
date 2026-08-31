from __future__ import annotations

import re
from typing import Any


def make_plan(prompt: str) -> list[dict[str, Any]]:
    p = prompt.lower()
    steps: list[str] = ["读取 Board / MCU profile", "列出并阅读 Core 工程文件"]
    if any(k in p for k in ("usart", "uart", "串口")):
        steps += ["检查 RCC 与 GPIO（USART1: PA9 TX / PA10 RX）", "配置 USART", "必要时配置 DMA/中断", "修改 HAL MSP 与 main"]
    elif any(k in p for k in ("pwm", "tim2", "定时器", "timer")):
        steps += ["确认 TIM 通道与 GPIO AF", "配置 TIM PWM", "启动 PWM"]
    elif any(k in p for k in ("adc",)):
        steps += ["确认 ADC 通道引脚", "配置 ADC（轮询或 DMA）"]
    elif any(k in p for k in ("i2c", "eeprom")):
        steps += ["确认 I2C 引脚（PB6/PB7）", "配置 I2C"]
    elif any(k in p for k in ("spi",)):
        steps += ["确认 SPI 引脚", "配置 SPI"]
    elif any(k in p for k in ("led", "闪", "blink", "gpio")):
        steps += ["读取板载 LED 引脚（Blue Pill = PC13）", "使能 GPIOC 时钟并初始化输出", "HAL_GPIO_TogglePin + HAL_Delay"]
    else:
        steps.append("按外设最小改动修改 Core/Src 与 Core/Inc")
    steps += ["compile_project", "根据真实 GCC/LD 错误修复", "Build 成功后静态分析（可选）"]
    return [{"id": f"s{i+1}", "index": i + 1, "title": t, "status": "pending"} for i, t in enumerate(steps)]


def looks_complex(prompt: str) -> bool:
    p = prompt.lower()
    keys = ("usart", "uart", "dma", "pwm", "tim", "adc", "i2c", "spi", "exti", "中断")
    return sum(1 for k in keys if k in p) >= 1 or len(re.findall(r"\w+", p)) > 12
