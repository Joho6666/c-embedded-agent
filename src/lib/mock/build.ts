import type { BuildResult, Problem } from "@/types/build";
import type { AgentTask } from "@/types/agent";
import type { CallStackFrame, Register, SerialLine, TestSuite, WatchVar } from "@/types/debug";

export const latestBuild: BuildResult = {
  number: 27,
  status: "success",
  durationSec: 4.2,
  flashUsedKb: 18.4,
  flashTotalKb: 64,
  ramUsedKb: 4.3,
  ramTotalKb: 20,
  warnings: 3,
  errors: 0,
  output: [
    "$ arm-none-eabi-gcc -mcpu=cortex-m3 -mthumb ...",
    "[1/18] Building main.c",
    "[18/18] Linking stm32_led.elf",
    "Build successful",
    "FLASH   18432 / 65536",
    "RAM      4380 / 20480",
  ],
};

export const problems: Problem[] = [
  { id: "e1", file: "main.c", line: 42, severity: "error", message: "GPIO_PIN_5 undeclared", suggestion: "在 gpio.h 中 #include \"stm32f1xx_hal.h\"", source: "gcc" },
  { id: "w1", file: "main.c", line: 18, severity: "warning", message: "unused variable 'tmp'", source: "clangd" },
  { id: "w2", file: "gpio.c", line: 11, severity: "warning", message: "implicit declaration of HAL_GPIO_WritePin", source: "gcc" },
];

export const serialLog: SerialLine[] = [
  { ts: "00:00:01.224", text: "System Init" },
  { ts: "00:00:01.428", text: "GPIO Init OK" },
  { ts: "00:00:02.001", text: "LED ON" },
  { ts: "00:00:02.501", text: "LED OFF" },
];

export const registers: Register[] = [
  { name: "R0", value: "0x00000001" },
  { name: "R1", value: "0x20000120" },
  { name: "PC", value: "0x08000428" },
  { name: "SP", value: "0x20004FE0" },
];

export const callStack: CallStackFrame[] = [
  { name: "main()", location: "main.c:24" },
  { name: "HAL_Delay()", location: "stm32f1xx_hal.c:412" },
  { name: "SysTick_Handler()", location: "stm32f1xx_it.c:9" },
];

export const watches: WatchVar[] = [
  { name: "led_state", value: "1" },
  { name: "counter", value: "238" },
];

export const testSuite: TestSuite = {
  name: "Unity / gpio_led",
  passed: 6,
  failed: 1,
  skipped: 1,
  coverage: 78.4,
  cases: [
    { name: "test_gpio_init_enables_clock", status: "pass", durationMs: 2 },
    { name: "test_toggle_changes_odr", status: "pass", durationMs: 3 },
    { name: "test_hardfault_handler_returns", status: "fail", durationMs: 4, message: "infinite loop stub" },
    { name: "test_usb_not_used", status: "skip", durationMs: 0 },
  ],
};

export const historyTasks: AgentTask[] = [
  { id: "t1", title: "实现 UART DMA", prompt: "USART1 DMA", status: "complete", createdAt: "2026-08-30 21:04", projectName: "STM32 智能温控器" },
  { id: "t2", title: "修复 HardFault", prompt: "检查栈与向量表", status: "complete", createdAt: "2026-08-29 11:18", projectName: "FreeRTOS Motor Controller" },
  { id: "t3", title: "配置 FreeRTOS Task", prompt: "LED / Motor / Telemetry", status: "working", createdAt: "2026-08-31 13:40", projectName: "FreeRTOS Motor Controller" },
  { id: "t4", title: "LED 500ms 闪烁", prompt: "STM32F103C8T6 使用 PA5 控制 LED，每500ms闪烁", status: "complete", createdAt: "2026-08-31 14:02", projectName: "STM32_LED_Project" },
];
