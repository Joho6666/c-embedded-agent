# MYOS_AUDIT.md

审计对象：本仓库当前主干（分支 `feat/workbench-2.0-ui`，产品名 `c-embedded-agent` 0.8.0-beta）。  
审计日期：2026-09-03。  
结论先行：**这是可用的 C-Agent MCU Workbench，不是空的 MyOS。** MyOS 必须叠加，不能推倒。

## 1. 当前架构

```
Next.js 15 App Router (src/)     FastAPI (backend/app/main.py)
  WorkbenchShell                   Agent runtime (SSE + tools)
  Zustand stores                   SQLite workspaces/agent.sqlite
  LIVE / DEMO / OFFLINE            STM32F103 HAL template + make/OpenOCD
```

- 前端：Next.js 15.5、React 19、Tailwind 4、Zustand、cmdk、react-resizable-panels、Monaco。
- 后端：FastAPI、pydantic-settings、httpx、pyserial。**没有** SQLAlchemy 在 Agent 主路径上。
- 工程：`workspaces/<id>/project.json` + 官方 `templates/stm32f103_hal_official`。
- 知识：SQLite FTS5 + `knowledge_sources/stm32f103`。
- leftover：`unigateway/`、`backend/app/models/database.py`（Gateway providers/credentials）、已删除的 `(console)` 控制台。pytest 忽略 `test_gateway.py` / `test_v090.py`。

## 2. 当前页面

一级（`src/components/layout/nav.ts`）：Home `/`、项目、Workspace、Agent、Debug、Knowledge、设置。

Workbench 2.0：

| 路由 | 实际职责 |
|---|---|
| `/` | Start Center（MCU 工程入口，不是 Today） |
| `/projects` `/projects/new` `/projects/[id]/configure` | 工程列表 / Multi-MCU Setup |
| `/workspace` `/agent` `/code` | IDE：Explorer + Editor + Agent 上下文 |
| `/debug` | Hardware Validation；GDB Not Available |
| `/knowledge` `/skills` `/memory/errors` `/ioc` `/mcu` `/tools` `/benchmark` `/history` | 工程工具 |
| `/credentials` `/models` `/playground` `/providers` | redirect 到 `/` |

Command Palette（Ctrl/Cmd+K）已存在，内容仍是 MCU 页面与演示操作。

## 3. 当前数据库

`backend/app/db.py` → `workspaces/agent.sqlite`：

- `runs` `run_events` `file_changes` `builds` `artifacts` `model_calls`
- `knowledge_fts`（FTS5）

**没有** Workspace / OS Project / Task / Agent registry / Automation / Activity / Memory Pack。  
Gateway SQLAlchemy 模型存在但未挂到 C-Agent `main.py`，视为死代码，不接入。

## 4. 当前 Agent 能力

单一嵌入式 Agent（`backend/app/agent/runtime.py`）：

- 真实：读工程、apply_patch、写保护、make 流式编译、Error Memory、IOC/Pin、OpenOCD flash、serial、validation、Stop cancel、SSE、审批门。
- Skills：`backend/app/skills/stm32f103.json` 外设配方（USART/ADC/PWM…），不是通用 Skill Registry。
- 不存在：Agent Registry、多 provider 执行、Task Assign、全局 Activity。

## 5. 当前优点

- 不伪造 Build/Flash/Hardware PASS。
- Agent 执行可追踪（事件、diff、approval、artifacts）。
- Workbench 壳已经是 Linear/VS Code 密度：紧凑 sidebar、可调整面板、Cmd+K。
- 测试覆盖 Stop / SSE / patch / hardware no-fake-pass / workspace template。

## 6. 当前问题（相对 MyOS 定位）

- 产品身份是 MCU Workbench，首页在问「开始什么固件工程」，不是「今天做什么」。
- Project 不是 OS 对象（无 Tasks/Docs/Activity/Owner/Deadline）。
- 不能把 Task 交给 Agent；只能在 `/agent` 输入 prompt。
- 无统一状态机（Task/Project/Agent/Run 各说各话）。
- 仓库内混有 Gateway、tongpin、hallotickets 等旁路目录，增加认知负担。

## 7. 技术债

- 未提交的 Workbench 2.0 与大量 untracked backend 文件同处于工作区。
- DEMO mock 工程仍写 PA5 LED（与 Blue Pill PC13 真实默认不一致）。
- `ProjectCard` 一律跳 `/workspace`，没有 Project OS 页。
- CI 只跑 `npm run build` + pytest，不跑 lint/typecheck/vitest。
- Gateway 模型 / `unigateway/` 仍在树内。

## 8. 可以保留的代码

WorkbenchShell、ToolBar、ActivityBar、AgentTimeline、PlanViewer、ApprovalCard、ArtifactList、runtime.py TOOLS、compiler/flash/validate、db.py runs 表、cmdk、LIVE/DEMO 模式、STM32 Support Matrix。

## 9. 应删除的代码（本轮不做物理删除）

不删除 `unigateway/` 与 Gateway tests（已 ignore）。不删除 MCU 页。本轮只避免再接入。

## 10. 应重构的代码

- `/` Start Center → `/start`；`/` 改为 Today。
- 导航：Today · Projects · Workspace · Agent · Knowledge · Settings。
- `ProjectCard` / 项目列表进入 `/projects/[id]`。
- `runs` 增加 `task_id`；runtime 结束时回写 Task 状态。

## 11. 与目标架构差距

| MyOS | 现状 | P0 |
|---|---|---|
| Today / Inbox | 无 | Today（Inbox 并入 Needs Review） |
| Project OS | MCU project.json | `os_projects` + 详情 tabs |
| Task + Assign Agent | 无 | tasks + 仅 c-agent 可跑 |
| Agent Registry | 单一 runtime | 表 + planned 行 |
| Activity | run_events | 结构化 `activities` |
| Automation / Context Pack | 无 | P1 |
| 多 Agent 执行 | 无 | P2 |

## 12. 推荐开发顺序

P0（本轮）：文档 → SQLite OS 层 → `/api/os` → Today + Project/Task → Assign C-Agent → Activity → Cmd+K → 测试。  
P1：Agents Control Center、Automation 三段式、Context Pack、Inbox、Memory。  
P2：多 Agent adapter、Semantic Search、GitHub 文件源。

## 评分

- 作为 STM32F103 Agent Workbench：**7.5 / 10**
- 作为 MyOS Work OS：**2.5 / 10**
