#!/usr/bin/env python3
"""Generate benchmark tasks 21-50 (Benchmark v2) with domain/level fields.

Also back-fills `domain`/`level` on the existing 20 tasks (regression level).
Deterministic — run once, commit the JSONs. Idempotent on re-run.
"""
from __future__ import annotations

import json
from pathlib import Path

DIR = Path(__file__).resolve().parent / "stm32f103"

NEW_TASKS = [
    # --- PERIPHERAL_CONFIG (capability) ---
    ("21", "配置 USART2 115200，每 500ms 发送一行 hello。", ["Core/Src/main.c", "Core/Src/usart.c"], "PERIPHERAL_CONFIG"),
    ("22", "USART1 printf 重定向，上电输出 CEA:USART:PASS。", ["Core/Src/main.c"], "PERIPHERAL_CONFIG"),
    ("23", "使用 SysTick 实现 1ms 时基，LED 每 500ms 翻转。", ["Core/Src/main.c"], "PERIPHERAL_CONFIG"),
    ("24", "PB0 上拉输入按键，按下时 LED 亮，松开灭。", ["Core/Src/main.c", "Core/Src/gpio.c"], "PERIPHERAL_CONFIG"),
    ("25", "TIM2 更新中断 1Hz，中断里翻转 PC13。", ["Core/Src/main.c"], "PERIPHERAL_CONFIG"),
    ("26", "TIM3 输出两路 PWM：PA6 占空比 25%，PA7 占空比 75%，1kHz。", ["Core/Src/main.c"], "PERIPHERAL_CONFIG"),
    ("27", "ADC1 双通道轮询采样 PA1/PA2， USART1 输出两路数值。", ["Core/Src/main.c"], "PERIPHERAL_CONFIG"),
    ("28", "I2C1 读写 24C02 EEPROM：写入 0xAB 到地址 0x00 再读回验证。", ["Core/Src/main.c"], "PERIPHERAL_CONFIG"),
    ("29", "SPI1 主模式发送 0x55 并用 MISO 回环接收验证。", ["Core/Src/main.c"], "PERIPHERAL_CONFIG"),
    ("30", "PB1 下降沿 EXTI 中断，中断中翻转 LED。", ["Core/Src/main.c"], "PERIPHERAL_CONFIG"),
    ("31", "USART1 DMA 循环模式接收，收到数据原样回发。", ["Core/Src/main.c"], "PERIPHERAL_CONFIG"),
    ("32", "ADC1 DMA 扫描两通道到缓冲区，TIM2 1Hz 触发 USART1 输出。", ["Core/Src/main.c"], "PERIPHERAL_CONFIG"),
    ("33", "TIM3 PWM 50Hz 驱动舵机，0.5ms~2.5ms 脉宽每秒步进。", ["Core/Src/main.c"], "PERIPHERAL_CONFIG"),
    # --- LONG_HORIZON (capability) ---
    ("34", "PWM 呼吸灯：TIM3 PA6 输出，占空比 0→100→0% 循环，周期 2 秒。", ["Core/Src/main.c"], "LONG_HORIZON"),
    ("35", "按键 EXTI 触发 LED 翻转，同时 USART1 输出按键次数。", ["Core/Src/main.c"], "LONG_HORIZON"),
    ("36", "USART1 接收命令 'LED ON'/'LED OFF' 控制 PC13，其他命令回显。", ["Core/Src/main.c"], "LONG_HORIZON"),
    ("47", "同时实现：LED 500ms 闪烁、USART1 输出、ADC1 PA1 采样，三者互不阻塞。", ["Core/Src/main.c"], "LONG_HORIZON"),
    ("48", "USART1 DMA 接收不定长数据，每秒通过 DMA 通道输出接收字节数统计。", ["Core/Src/main.c"], "LONG_HORIZON"),
    ("49", "USART1 中断接收实现回显，USART2 每 1s 输出心跳 CEA:USART:PASS。", ["Core/Src/main.c", "Core/Src/usart.c"], "PERIPHERAL_CONFIG"),
    ("50", "双串口日志：USART1 打印调试信息，USART2 输出 ADC1 采样均值（1Hz）。", ["Core/Src/main.c"], "LONG_HORIZON"),
    # --- COMPILE_REPAIR (capability, with injected fault) ---
    ("37", "Blue Pill 板载 LED 每 500ms 闪烁。", ["Core/Src/main.c", "Core/Src/gpio.c"], "COMPILE_REPAIR",
     [{"file": "Core/Src/main.c", "find": "LED_Pin", "replace": "GPIO_PIN_99", "count": 1}]),
    ("38", "USART1 115200 发送 hello。", ["Core/Src/main.c", "Core/Src/usart.c"], "COMPILE_REPAIR",
     [{"file": "Core/Src/main.c", "find": "SystemClock_Config();", "replace": "SystemClock_ConfigX();", "count": 1}]),
    ("39", "TIM3 PWM 1kHz 50% 占空比输出到 PA6。", ["Core/Src/main.c", "Core/Src/tim.c"], "COMPILE_REPAIR",
     [{"file": "Core/Src/main.c", "find": "MX_GPIO_Init();", "replace": "MX_GPIO_Init();\n  DEBUG_TriggerFault();", "count": 1}]),
    # --- SAFETY (capability) ---
    ("40", "USART1 中断接收每字节并立即在 ISR 中处理协议解析（注意中断安全）。", ["Core/Src/main.c"], "SAFETY"),
    ("41", "EXTI 按键中断置标志，主循环查询标志处理，不得在中断里延时。", ["Core/Src/main.c"], "SAFETY"),
    ("42", "USART1 DMA 收发 + 空闲中断，注意与主循环的共享缓冲区 volatile 正确性。", ["Core/Src/main.c"], "SAFETY"),
    # --- DEBUGGING (capability; symptom-driven prompts with injected defects) ---
    ("43", "排障：上一位工程师写的 USART1 代码烧进去后串口无输出，请修复并保证上电输出 CEA:USART:PASS。",
     ["Core/Src/main.c"], "DEBUGGING",
     [{"file": "Core/Src/main.c", "find": "SystemClock_Config();", "replace": "SystemClock_Config();\n  /* BUG: USART was never initialized here */", "count": 1}]),
    ("44", "排障：LED 不闪烁。工程能编译但 PC13 无现象，请找出问题并修复。",
     ["Core/Src/main.c", "Core/Src/gpio.c"], "DEBUGGING",
     [{"file": "Core/Src/main.c", "find": "HAL_Delay(500)", "replace": "HAL_Delay(500000)", "count": 1}]),
    # --- CONTEXT (capability; board-profile faithful) ---
    ("45", "按 Blue Pill 板卡定义配置 USART1 引脚（严格使用板卡 profile 的 TX/RX 引脚），115200。", ["Core/Src/main.c", "Core/Src/usart.c"], "CONTEXT"),
    ("46", "按 Blue Pill 板卡定义配置板载 LED 引脚并 250ms 快闪，同时输出时钟配置说明到注释。",
     ["Core/Src/main.c", "Core/Src/gpio.c"], "CONTEXT"),
]

# existing 1-20 → domain/level back-fill
EXISTING_DOMAIN = {
    "01": "PERIPHERAL_CONFIG", "02": "PERIPHERAL_CONFIG", "03": "PERIPHERAL_CONFIG",
    "04": "PERIPHERAL_CONFIG", "05": "PERIPHERAL_CONFIG", "06": "PERIPHERAL_CONFIG",
    "07": "PERIPHERAL_CONFIG", "08": "PERIPHERAL_CONFIG", "09": "PERIPHERAL_CONFIG",
    "10": "PERIPHERAL_CONFIG", "11": "PERIPHERAL_CONFIG", "12": "PERIPHERAL_CONFIG",
    "13": "PERIPHERAL_CONFIG", "14": "PERIPHERAL_CONFIG", "15": "PERIPHERAL_CONFIG",
    "16": "PERIPHERAL_CONFIG", "17": "PERIPHERAL_CONFIG", "18": "PERIPHERAL_CONFIG",
    "19": "PERIPHERAL_CONFIG", "20": "LONG_HORIZON",
}


def main() -> int:
    # back-fill existing
    for p in sorted(DIR.glob("*.json")):
        task = json.loads(p.read_text(encoding="utf-8"))
        changed = False
        if "domain" not in task:
            task["domain"] = EXISTING_DOMAIN.get(task.get("id") or "", "PERIPHERAL_CONFIG")
            changed = True
        if "level" not in task:
            task["level"] = "regression"
            changed = True
        if "inject" not in task:
            task["inject"] = []
            changed = True
        if changed:
            p.write_text(json.dumps(task, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")

    for tid, prompt, expected, domain, *rest in NEW_TASKS:
        inject = rest[0] if rest else []
        path = DIR / f"{tid}_task.json"
        path.write_text(
            json.dumps(
                {
                    "id": tid,
                    "prompt": prompt,
                    "expected_files": expected,
                    "must_compile": True,
                    "domain": domain,
                    "level": "capability",
                    "inject": inject,
                },
                ensure_ascii=False,
                indent=0,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"wrote {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
