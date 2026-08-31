import type { AgentStep, PlanStep } from "@/types/agent";

export const DEMO_PROMPT = "STM32F103C8T6 使用 PA5 控制 LED，每500ms闪烁";

export const demoPlan: PlanStep[] = [
  { id: "p1", index: 1, title: "分析需求", status: "pending" },
  { id: "p2", index: 2, title: "检测 MCU", status: "pending" },
  { id: "p3", index: 3, title: "确认 GPIO", status: "pending" },
  { id: "p4", index: 4, title: "配置 Clock", status: "pending" },
  { id: "p5", index: 5, title: "配置 GPIO", status: "pending" },
  { id: "p6", index: 6, title: "编写 main.c", status: "pending" },
  { id: "p7", index: 7, title: "Build", status: "pending" },
  { id: "p8", index: 8, title: "Static Analysis", status: "pending" },
  { id: "p9", index: 9, title: "Flash", status: "pending" },
  { id: "p10", index: 10, title: "Serial Verification", status: "pending" },
];

export interface DemoEvent {
  delay: number;
  statusText: string;
  planId?: string;
  planStatus?: PlanStep["status"];
  step?: AgentStep;
  terminal?: string[];
  serial?: { ts: string; text: string }[];
  showDiff?: boolean;
  buildPhase?: "error" | "success" | "flash" | "idle";
  problemsActive?: boolean;
}

export const demoEvents: DemoEvent[] = [
  {
    delay: 400,
    statusText: "正在分析需求...",
    planId: "p1",
    planStatus: "running",
    step: { id: "s1", title: "分析需求", detail: "STM32F103C8T6 · PA5 · 500ms 翻转", status: "running" },
    terminal: ["$ agent run --task led-blink", "parse requirement ..."],
  },
  {
    delay: 1200,
    statusText: "正在识别 MCU...",
    planId: "p1",
    planStatus: "success",
    step: { id: "s1", title: "分析开发板", detail: "STM32F103C8T6", status: "success" },
  },
  {
    delay: 900,
    statusText: "正在检测开发环境...",
    planId: "p2",
    planStatus: "running",
    step: { id: "s2", title: "检测开发环境", detail: "ARM GCC 13.2", status: "success" },
    terminal: ["$ arm-none-eabi-gcc --version", "arm-none-eabi-gcc (GNU Arm Embedded) 13.2.1"],
  },
  {
    delay: 1100,
    statusText: "正在读取 STM32F103 Datasheet...",
    planId: "p2",
    planStatus: "success",
    step: {
      id: "s3",
      title: "读取知识库",
      detail: "STM32F103 Reference Manual · RM0008",
      status: "success",
      toolCall: {
        tool: "knowledge.search",
        command: "index query --doc RM0008 --q GPIOA PA5",
        result: "PA5 · GPIOA · AF SPI1_SCK / TIM2_CH1",
        status: "success",
      },
    },
    terminal: ["open knowledge://RM0008", "hit: GPIOA PIN5 · page 166"],
  },
  {
    delay: 1000,
    statusText: "正在分析 GPIO...",
    planId: "p3",
    planStatus: "running",
    step: { id: "s4", title: "分析 GPIO", detail: "PA5 → GPIOA · Output PP", status: "success" },
  },
  {
    delay: 900,
    statusText: "正在分析 RCC 时钟配置...",
    planId: "p3",
    planStatus: "success",
    step: { id: "s5", title: "分析系统时钟", detail: "HSE 8 MHz × PLL9 = 72 MHz", status: "success" },
  },
  {
    delay: 800,
    statusText: "正在创建工程...",
    planId: "p4",
    planStatus: "success",
    step: { id: "s6", title: "创建工程", detail: "STM32_LED_Project · HAL · ARM GCC", status: "success" },
  },
  {
    delay: 1400,
    statusText: "正在生成 main.c...",
    planId: "p5",
    planStatus: "success",
    step: {
      id: "s7",
      title: "生成代码",
      detail: "main.c · gpio.c · gpio.h",
      status: "success",
      files: ["main.c", "gpio.c", "gpio.h"],
    },
    terminal: ["write Core/Src/main.c", "write Core/Src/gpio.c", "write Core/Inc/gpio.h"],
  },
  {
    delay: 600,
    statusText: "正在执行 ARM GCC...",
    planId: "p7",
    planStatus: "running",
    step: {
      id: "s8",
      title: "正在编译",
      detail: "make -j8",
      status: "running",
      toolCall: { tool: "arm-none-eabi-gcc", command: "make -j8", status: "running" },
    },
    terminal: ["$ make -j8", "[1/18] Building main.c", "[2/18] Building gpio.c"],
    buildPhase: "idle",
  },
  {
    delay: 1600,
    statusText: "Build failed · 正在分析编译错误...",
    planId: "p7",
    planStatus: "failed",
    problemsActive: true,
    step: {
      id: "s8",
      title: "正在编译",
      detail: "Build failed",
      status: "failed",
      toolCall: {
        tool: "arm-none-eabi-gcc",
        command: "make -j8",
        result: "main.c:42: error: GPIO_PIN_5 undeclared",
        status: "failed",
      },
    },
    terminal: [
      "main.c:42:13: error: ‘GPIO_PIN_5’ undeclared (first use in this function)",
      "make: *** [main.o] Error 1",
      "Build failed",
    ],
    buildPhase: "error",
  },
  {
    delay: 1400,
    statusText: "正在修复 GPIO_PIN_5 定义...",
    step: { id: "s9", title: "分析编译错误", detail: "gpio.h 缺少 stm32f1xx_hal.h", status: "success" },
    showDiff: true,
    terminal: ["agent fix --file Core/Inc/gpio.h", "include stm32f1xx_hal.h"],
  },
  {
    delay: 900,
    statusText: "已修复 GPIO_PIN_5 定义 · 重新编译",
    planId: "p7",
    planStatus: "running",
    step: {
      id: "s10",
      title: "已修复 GPIO_PIN_5 定义",
      detail: "gpio.h ← #include \"stm32f1xx_hal.h\"",
      status: "success",
      files: ["gpio.h"],
    },
  },
  {
    delay: 1500,
    statusText: "重新编译中...",
    step: {
      id: "s11",
      title: "重新编译",
      detail: "make -j8",
      status: "running",
      toolCall: { tool: "arm-none-eabi-gcc", command: "make -j8", status: "running" },
    },
    terminal: ["$ make -j8", "[1/18] Building main.c", "[2/18] Building gpio.c", "..."],
  },
  {
    delay: 1400,
    statusText: "Build Successful",
    planId: "p7",
    planStatus: "success",
    problemsActive: false,
    step: {
      id: "s11",
      title: "Build Successful",
      detail: "Flash 18.4 KB / RAM 4.3 KB",
      status: "success",
      toolCall: {
        tool: "arm-none-eabi-gcc",
        command: "make -j8",
        result: "FLASH 18432 / 65536 · RAM 4380 / 20480",
        status: "success",
      },
    },
    terminal: ["[18/18] Linking stm32_led.elf", "Build successful", "FLASH   18432 / 65536", "RAM      4380 / 20480"],
    buildPhase: "success",
  },
  {
    delay: 800,
    statusText: "正在静态检查...",
    planId: "p8",
    planStatus: "running",
    step: {
      id: "s12",
      title: "静态检查",
      detail: "Cppcheck · 0 error",
      status: "success",
      toolCall: {
        tool: "cppcheck",
        command: "cppcheck --enable=all Core/",
        result: "0 error / 3 style",
        status: "success",
      },
    },
  },
  {
    delay: 1100,
    statusText: "正在烧录固件...",
    planId: "p8",
    planStatus: "success",
    step: {
      id: "s13",
      title: "Flash Firmware",
      detail: "OpenOCD · ST-Link · 0x08000000",
      status: "running",
      toolCall: {
        tool: "openocd",
        command:
          "openocd -f interface/stlink.cfg -f target/stm32f1x.cfg -c 'program stm32_led.hex verify reset exit'",
        status: "running",
      },
    },
    terminal: [
      "$ openocd -f interface/stlink.cfg -f target/stm32f1x.cfg",
      "Info : STLINK V2 detected",
      "target halted due to debug-request, current mode: Thread",
    ],
    buildPhase: "flash",
  },
  {
    delay: 1300,
    statusText: "烧录完成 · 正在读取串口...",
    planId: "p9",
    planStatus: "success",
    step: {
      id: "s13",
      title: "Flash Firmware",
      detail: "verified · reset",
      status: "success",
      toolCall: {
        tool: "openocd",
        command: "program stm32_led.hex verify reset exit",
        result: "verified 18432 bytes",
        status: "success",
      },
    },
    terminal: ["** Programming Finished **", "** Verify OK **", "reset halt → reset run"],
  },
  {
    delay: 700,
    statusText: "正在读取串口日志...",
    planId: "p10",
    planStatus: "running",
    serial: [
      { ts: "00:00:01.224", text: "System Init" },
      { ts: "00:00:01.428", text: "GPIO Init OK" },
    ],
    terminal: ["$ serial --port COM3 --baud 115200", "connected COM3 115200"],
  },
  { delay: 600, statusText: "LED ON", serial: [{ ts: "00:00:02.001", text: "LED ON" }] },
  { delay: 500, statusText: "LED OFF", serial: [{ ts: "00:00:02.501", text: "LED OFF" }] },
  { delay: 500, statusText: "LED ON", serial: [{ ts: "00:00:03.001", text: "LED ON" }] },
  {
    delay: 800,
    statusText: "Validation Passed",
    planId: "p10",
    planStatus: "success",
    step: {
      id: "s14",
      title: "Validation Passed",
      detail: "LED 周期 1000ms · 符合 500ms 翻转预期",
      status: "success",
    },
    serial: [{ ts: "00:00:03.501", text: "LED OFF" }],
    terminal: ["period ≈ 1000ms (ON 500 + OFF 500)", "validation: PASS"],
    buildPhase: "success",
  },
];
