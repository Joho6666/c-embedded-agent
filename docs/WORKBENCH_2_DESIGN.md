# Workbench 2.0 Design

产品定位：VS Code + PlatformIO + STM32CubeIDE + AI Agent，不是 ChatGPT 卡片墙。

## 视觉

- Dark 优先：`#050506` / `#08090c` / `#0c0d11` / `#26272e`
- Primary 蓝，Success 绿，Warning 黄，Error 红
- 圆角 5–8px，Lucide 图标，代码/数据用等宽字体
- 禁止大面积渐变、巨大圆角、玻璃拟态、Emoji 图标、无意义统计卡

## 页面

### Start Center `/`

回答「现在要开始什么工程？」：AI Intake、快捷入口、Recent Projects、Environment、Connected Devices、Templates。

未实现导入标 Coming Soon。Environment 在 DEMO/OFFLINE 为 UNKNOWN。

### Multi-MCU Setup `/projects/new`

左侧 PlatformDefinition 动态表单，右侧工程预览。STM32F103 + HAL + ARM GCC 走真实 `POST /api/projects`。其他平台创建 UI Preview，明确不会生成可编译固件。

### Workspace `/workspace`

Activity Bar · Explorer · Code Editor · Agent（会话 / 执行计划 / 硬件上下文 / 知识库）· BottomDock（Problems / Output / Terminal / Serial）。

Agent 以 Execution Plan + evidence 为主，不是聊天机器人。Suggested Fix 仅在真实 validation evidence 出现时显示。

### Debug `/debug`

GDB 区全部 Not Available。Hardware Validation Timeline / Serial / Flash Log / Hardware Result / Auto Diagnosis 绑定真实 pipeline，无证据不写 PASS。

## 导航

一级：Home · Projects · Workspace · Agent · Debug · Knowledge · Settings

Workspace 内 Activity：Explorer · Agent · Search · Build · Debug · Hardware · Problems

MCU / IOC / Skills / Error Memory / Tools / Benchmark / Serial 进入 Engineering Tools 或 Knowledge。

## 语言

中文 UI + 必要技术英文（Build、Debug、UART、GPIO、ESP-IDF、STM32CubeMX）。

## 响应式

目标 1440×900 / 1600×900 / 1920×1080。手机只保留 Projects / Agent Status / Approval / Build / Hardware Status。
