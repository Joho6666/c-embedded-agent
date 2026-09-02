# Workbench 2.0 UI Audit

审计对象：`C-Embedded Agent` 0.8.0-beta（本仓库前端 `src/` + FastAPI `backend/`）。

## 1. 重构前信息架构

一级导航原先 14 项：总览 / Agent / 项目 / 文件 / 芯片 / IOC / Skills / 知识库 / 错误记忆 / 验证 / 工具 / 测试 / 历史 / 设置。

Home 是 Engineering Dashboard（KPI + 快捷卡片），不是工程入口。`/agent` 是厨房水槽：文件树 + 时间线/代码/硬件 + 六个右栏面板叠在一起。Build / Serial / Debug 同时存在完整页面和 BottomPanel。

## 2. 可复用组件

- `AppShell` 思路与 `react-resizable-panels`
- Monaco `CodeEditor` / `FileTree`
- `AgentTimeline` `PlanViewer` `ApprovalCard` `ArtifactList` `PatchWhy`
- `HardwareTimeline` `HardwareRunButton` `CapabilityBanner`
- 暗色 token：background `#050506` chrome `#08090c` panel `#0c0d11` border `#26272e`

## 3. 重复组件

- HardwareContextPanel / ContextInspector / DevicePanel 重复 MCU 事实
- PinMap vs IocPinout
- 完整页 vs BottomPanel：Problems / Terminal / Serial / Debug
- 假 Flash 文案出现在 TopBar 与快捷键

## 4. 应重构组件

- `/` Dashboard → Start Center
- 14 项 Sidebar → Home / Projects / Workspace / Agent / Debug / Knowledge / Settings
- STM32 硬编码 TopBar → `ToolBar` + `PlatformDefinition`
- `/projects/new` 假装全平台可用 → 动态表单 + Planned 标记
- `/debug` DEMO 假寄存器 → Not Available
- `FileTree` 根名 `STM32_LED_Project`

## 5. STM32-specific UI 耦合点

- TopBar `$ STM32_Programmer_CLI`
- mock 工具默认 connected（CubeMX / Keil / COM3）
- MCU 目录含 F407 / ESP32-S3 / STC89C52 且无状态区分
- HardwareContext 默认 debugger=ST-Link、serial=COM3
- Agent 演示按钮写死 STM32 LED

## 6. Multi-MCU 所需抽象

统一 `PlatformDefinition`：id / frameworks / toolchains / boards / flashAdapters / debugAdapters / skills / toolbarActions / status。

UI 按目录渲染。Skills 由平台过滤（C51 无 Wi-Fi，Host C 无 ST-Link）。

## 7. 本轮实施

- Start Center `/`
- Multi-MCU `/projects/new` 与 `/projects/[id]/configure`
- Workspace `/workspace`（`/agent` `/code` 进入同一壳）
- Debug & Validation `/debug`（`/validation` 重定向）
- `GET /api/environment` `GET /api/devices`
- 状态枚举 PASS / FAIL / PARTIAL / UNKNOWN / UNAVAILABLE / NOT TESTED
- 不修改 README Support Matrix；ESP32 / C51 仍为 Planned
