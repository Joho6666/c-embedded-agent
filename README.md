# C-Embedded Agent

**专注 C 语言与嵌入式开发的 AI 工程师工作台。**

这不是通用聊天机器人，也不是 ChatGPT 套皮界面。它是一个面向桌面端的专业 Coding Agent Prototype，把 STM32 / ESP32 / 8051 / FreeRTOS / 裸机 C 的完整工程闭环可视化出来：

需求分析 → 识别 MCU → 读取芯片知识库 → 分析引脚 / 时钟 / 外设 → 生成工程与 C/H 文件 → 编译 → 读 Error / Warning → 自动修复 → 静态检查 → 单元测试 → 生成 HEX / BIN → 烧录 → 读取串口日志 → 判断运行结果。

前端要体现的是：**AI 正在像真正的嵌入式工程师一样工作**，而不是只吐一段回答。

> 当前仓库是完整可交互的前端 Prototype。数据全部 Mock，组件和 `services/` 已按真实 API 预留，方便后续接编译器、OpenOCD、串口和知识库后端。

---

## 产品定位

| 它是 | 它不是 |
| --- | --- |
| Cursor + VS Code + 嵌入式 IDE + Agent | 普通 AI 聊天窗 |
| 高信息密度的工程师工具 | 花哨渐变 / 卡通机器人 |
| 工具调用、编译、烧录、串口可追踪 | 只给最终代码块 |
| 默认深色、小圆角、紧凑布局 | 大留白的消费级 Chat UI |

面向场景：

- STM32 / ARM Cortex-M / CMSIS / HAL / LL
- ESP32 / ESP-IDF
- C51 / 8051 / STC
- FreeRTOS / 裸机 C / Embedded Linux C
- PlatformIO / Keil / GCC / CMake
- OpenOCD / ST-Link / 串口验证

---

## 界面结构

桌面 Web App，对标 1440×900 / 1920×1080。

```
┌──────────────────────────────────────────────────────────┐
│ Top Bar：Logo / 项目 / MCU / Git / Agent 状态 / Build Flash │
├────────────┬───────────────────────────┬──────────────────┤
│ Sidebar    │        主工作区            │  右栏 Context    │
│ Agent 项目  │  Timeline / 代码 / 芯片    │  Plan / Diff /   │
│ 文件 芯片   │                           │  MCU / 串口分析  │
│ 知识库 工具 │                           │                  │
├────────────┴───────────────────────────┴──────────────────┤
│ Bottom：Terminal · Build · Problems · Serial · Debug      │
└──────────────────────────────────────────────────────────┘
```

- 面板可拖拽改宽度
- Sidebar 可折叠
- 底栏 Terminal 在 workspace 页常驻
- 命令面板：`Ctrl + K`
- 默认 Dark Mode，设置页可切 Light
- 手机只保留 Dashboard / Agent / 项目 / Build 状态，不做完整 IDE

---

## 页面一览

| 路由 | 页面 | 说明 |
| --- | --- | --- |
| `/` | Dashboard | 项目数、Build 成功率、最近工程、Recent Agent Tasks |
| `/agent` | Agent Workspace | 任务条 + Timeline + Tool Call + 命令式输入 |
| `/projects` | 项目列表 | MCU / Framework / 编译器 / Build 状态 |
| `/projects/new` | 新建项目 | 平台 → MCU → 框架 → 工具链，四步向导 |
| `/code` | Code Editor | 文件树 + Monaco + AI Diff（Accept / Reject） |
| `/mcu` | 芯片信息 | Cortex-M3 / 72 MHz / Flash RAM / 外设数量 |
| `/mcu/pins` | Pin Configuration | 简化 LQFP48 引脚图，PA5 = LED |
| `/knowledge` | 知识库 | STM32 / ESP32 / C / RTOS 文档与 Indexed 状态 |
| `/tools` | 工具管理 | ARM GCC、clangd、Cppcheck、OpenOCD、ST-Link、COM3 |
| `/build` | Build | Build #27、Flash/RAM 占用、Terminal 输出 |
| `/problems` | Problems | Error / Warning + Ask Agent / Fix |
| `/testing` | 测试 | Unity / Ceedling Mock 结果与覆盖率 |
| `/serial` | Serial Monitor | COM3 115200 + AI 周期分析 |
| `/debug` | Debug | 寄存器、Call Stack、Watch |
| `/history` | 历史记录 | 任务时间线，可回放 Demo |
| `/settings` | 设置 | 主题、工具链、快捷键 |

---

## STM32 LED Demo

这是首页最重要的演示。在 Dashboard 或 Agent 页点击 **STM32 LED Demo** / **Run Agent**。

预填任务：

```text
STM32F103C8T6 使用 PA5 控制 LED，每500ms闪烁
```

前端会自动模拟完整闭环（约 20–30 秒，可 Stop）：

1. 分析需求，识别 STM32F103C8T6
2. 检测 ARM GCC 13.2
3. 读取 RM0008 / Datasheet，分析 PA5 → GPIOA
4. 配置 72 MHz 时钟，生成 `main.c` / `gpio.c` / `gpio.h`
5. `make -j8` **编译失败**：`GPIO_PIN_5 undeclared`
6. Agent 修复 `gpio.h`（补 `#include "stm32f1xx_hal.h"`），代码页出现红/绿 Diff
7. 重新编译成功：Flash 18.4 KB / RAM 4.3 KB
8. Cppcheck 静态检查
9. OpenOCD + ST-Link 烧录
10. 串口出现 `LED ON` / `LED OFF`，周期 1000ms，**Validation Passed**

同步表现：

- 主区 Agent Timeline 逐步 ✓ / ●
- 右栏 Plan 同步 pending / running / success / failed
- 底栏 Terminal 流式输出
- TopBar 状态文案跟随当前步骤
- 代码页可 Accept / Reject / Accept All

---

## 快捷键

| 快捷键 | 作用 |
| --- | --- |
| `Ctrl + K` | Agent Command 命令面板 |
| `Ctrl + B` | Build |
| `Ctrl + Shift + F` | Flash |
| `` Ctrl + ` `` | 显示 / 隐藏 Terminal |

---

## 技术栈

- Next.js 15 App Router
- React 19 + TypeScript
- Tailwind CSS 4
- shadcn/ui 风格组件 + Lucide
- Monaco Editor（关闭 SSR）
- `react-resizable-panels`
- `next-themes`（默认 dark）
- `cmdk` 命令面板
- Zustand（仅客户端 UI / Demo 时间轴）

前期不接真实后端。页面通过 `src/lib/services/` 取数，函数签名按未来 API 预留。

```
src/
  app/(workspace)/     IDE 壳与 16 个页面
  components/          Agent / Build / MCU / Editor / Terminal ...
  lib/mock/            项目、芯片、知识库、工具、Demo 脚本
  lib/services/        agent / project / build / mcu / knowledge / tools
  lib/stores/          workspace 状态与 Demo 驱动
  types/               领域类型
```

---

## 本地运行

需要 Node.js 18+。

```bash
npm install
npm run dev
```

打开 [http://localhost:3000](http://localhost:3000)。

```bash
npm run build    # 生产构建
npm start        # 预览生产包
```

工作区根目录若还有其它 sibling 项目，它们已被 `.gitignore` 排除，不会进入本仓库。

---

## 语言

整个 UI 使用中文。MCU 名称、Compiler、HAL、FreeRTOS、GPIO 等专业术语保留英文。关键状态中英并列，例如：

**构建成功 / Build Successful**

---

## 后续接入方向

`services/` 现在返回带短延迟的 Mock Promise。真实后端可以按同一接口替换：

- 工程生成与文件树
- `arm-none-eabi-gcc` / PlatformIO 编译日志
- OpenOCD / ST-Link 烧录
- 串口 Monitor
- Datasheet / Reference Manual Embedding
- clangd / Cppcheck / Unity

Agent 操作应继续保持透明：调用了什么工具、读了什么资料、改了哪个文件、为什么改、Build 是否成功、硬件是否验证成功。
