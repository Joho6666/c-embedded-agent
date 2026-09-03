import type { AgentEvent } from "@/types/events";
import type { PlanStep } from "@/types/agent";
import { GPIO_H_ORIGINAL, GPIO_H_PROPOSED } from "./files";

export const goldenPlan: PlanStep[] = [
  { id: "p1", index: 1, title: "分析需求与硬件上下文", status: "pending" },
  { id: "p2", index: 2, title: "检索 RM0008 手册", status: "pending" },
  { id: "p3", index: 3, title: "STM32CubeMX 生成工程", status: "pending" },
  { id: "p4", index: 4, title: "ARM GCC 编译", status: "pending" },
  { id: "p5", index: 5, title: "补丁与重新编译", status: "pending" },
  { id: "p6", index: 6, title: "静态检查", status: "pending" },
  { id: "p7", index: 7, title: "烧录确认", status: "pending" },
  { id: "p8", index: 8, title: "串口验证", status: "pending" },
];

export interface GoldenStep {
  delay: number;
  planId?: string;
  planStatus?: PlanStep["status"];
  waitApproval?: boolean;
  event: Omit<AgentEvent, "id" | "runId" | "timestamp">;
}

export const goldenSteps: GoldenStep[] = [
  {
    delay: 400,
    planId: "p1",
    planStatus: "running",
    event: {
      type: "plan",
      status: "running",
      title: "制定计划",
      description: "STM32F103C8T6 · Blue Pill · PA5 LED · 500ms",
    },
  },
  {
    delay: 700,
    planId: "p1",
    planStatus: "success",
    event: {
      type: "reasoning",
      status: "success",
      title: "硬件上下文",
      description: "PA5 属于 GPIOA，需要开启 RCC GPIOA 时钟。框架 HAL，时钟 72 MHz。",
    },
  },
  {
    delay: 600,
    planId: "p2",
    planStatus: "running",
    event: {
      type: "knowledge_query",
      status: "running",
      title: "检索知识库",
      description: "查询：STM32F103 GPIOA PA5 输出配置 · MCU=STM32F103 · 框架 HAL",
    },
  },
  {
    delay: 900,
    planId: "p2",
    planStatus: "success",
    event: {
      type: "knowledge_result",
      status: "success",
      title: "知识命中",
      description: "RM0008 相关度 0.94 · stm32f1xx_hal_gpio.c 0.91 · GPIO_IOToggle 0.88",
      source: { title: "STM32F103 Reference Manual", uri: "RM0008", page: 166, section: "9.2 GPIO", score: 0.94 },
    },
  },
  {
    delay: 700,
    planId: "p3",
    planStatus: "running",
    event: {
      type: "tool_call",
      status: "running",
      title: "STM32CubeMX",
      tool: { name: "STM32CubeMX", command: "STM32CubeMX -q project.script" },
    },
  },
  {
    delay: 800,
    planId: "p3",
    planStatus: "success",
    event: {
      type: "tool_result",
      status: "success",
      title: "CubeMX 生成完成",
      description: "退出码 0 · 耗时 1.8s",
      tool: { name: "STM32CubeMX", command: "STM32CubeMX -q project.script", exitCode: 0 },
      durationMs: 1800,
      files: ["main.c", "gpio.c", "gpio.h"],
    },
  },
  {
    delay: 500,
    event: {
      type: "file_write",
      status: "success",
      title: "生成源文件",
      files: ["main.c", "gpio.c", "gpio.h"],
      artifacts: [],
    },
  },
  {
    delay: 500,
    event: {
      type: "pin_conflict",
      status: "waiting_approval",
      title: "⚠ 引脚冲突 PA9",
      description: "当前：USART1_TX · 请求：TIM1_CH2。检测到硬件冲突，需要确认是否重新分配 PA9。",
      requiresApproval: true,
      risk: "medium",
    },
    waitApproval: true,
  },
  {
    delay: 400,
    planId: "p4",
    planStatus: "running",
    event: {
      type: "compile",
      status: "running",
      title: "ARM GCC",
      tool: { name: "ARM GCC", command: "make -j8" },
    },
  },
  {
    delay: 1100,
    planId: "p4",
    planStatus: "failed",
    event: {
      type: "compile",
      status: "failed",
      title: "构建失败",
      description: "2 个错误 · 3 个警告",
      tool: { name: "ARM GCC", command: "make -j8", exitCode: 1 },
      output: "main.c:42:13: error: ‘GPIO_PIN_5’ undeclared",
      diagnostics: [
        {
          id: "d1",
          source: "gcc",
          severity: "error",
          path: "main.c",
          line: 42,
          message: "GPIO_PIN_5 undeclared",
          suggestion: "include stm32f1xx_hal.h in gpio.h",
        },
      ],
    },
  },
  {
    delay: 800,
    planId: "p5",
    planStatus: "running",
    event: {
      type: "file_diff",
      status: "waiting_approval",
      title: "AI 提出代码修改",
      description: "gpio.h 增加 #include \"stm32f1xx_hal.h\"",
      files: ["/Core/Inc/gpio.h"],
      original: GPIO_H_ORIGINAL,
      proposed: GPIO_H_PROPOSED,
      requiresApproval: true,
      risk: "low",
    },
    waitApproval: true,
  },
  {
    delay: 900,
    event: {
      type: "compile",
      status: "success",
      title: "构建成功",
      description: "Flash 18.4 KB / RAM 4.3 KB",
      tool: { name: "ARM GCC", command: "make -j8", exitCode: 0 },
      artifacts: [],
    },
  },
  {
    delay: 600,
    planId: "p6",
    planStatus: "success",
    event: {
      type: "tool_result",
      status: "success",
      title: "Cppcheck",
      description: "0 个错误 / 3 条风格提示",
      tool: { name: "Cppcheck", command: "cppcheck --enable=all Core/", exitCode: 0 },
    },
  },
  {
    delay: 500,
    planId: "p7",
    planStatus: "running",
    event: {
      type: "approval",
      status: "waiting_approval",
      title: "烧录确认",
      description: "即将修改固件并覆盖当前 Flash。风险：中。",
      requiresApproval: true,
      risk: "medium",
    },
    waitApproval: true,
  },
  {
    delay: 900,
    planId: "p7",
    planStatus: "success",
    event: {
      type: "flash",
      status: "success",
      title: "STM32CubeProgrammer",
      description: "已校验 18432 字节 · 复位",
      tool: {
        name: "STM32CubeProgrammer",
        command: "STM32_Programmer_CLI -c port=SWD -w stm32_led.hex 0x08000000",
        exitCode: 0,
      },
      artifacts: [],
    },
  },
  {
    delay: 500,
    planId: "p8",
    planStatus: "running",
    event: {
      type: "serial",
      status: "running",
      title: "读取串口",
      output: "[00:00:01.224] System Init",
    },
  },
  {
    delay: 500,
    event: { type: "serial", status: "running", title: "LED 亮", output: "[00:00:02.001] LED ON" },
  },
  {
    delay: 500,
    event: { type: "serial", status: "running", title: "LED 灭", output: "[00:00:02.501] LED OFF" },
  },
  {
    delay: 700,
    planId: "p8",
    planStatus: "success",
    event: {
      type: "validation",
      status: "success",
      title: "验证通过",
      description: "期望 500ms · 实测 499–501ms · 方法：串口时间戳",
    },
  },
];
