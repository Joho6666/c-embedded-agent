# MYOS_ARCHITECTURE_V2.md

MyOS 是叠在 C-Agent Workbench 上的 AI Work OS 层。固件工程能力不变；C-Agent 是第一个真实 Agent。

## 产品闭环（P0）

```
Project → Task → Assign C-Agent → build_context → runtime 执行
      → Artifact / SSE → Human Review → Task Done
      → Progress + Activity → Today
```

Codex / Claude Code / Grok 仅登记为 `planned`，Assign 返回 409，不假执行。

## Frontend Architecture

- 继续 `src/app/(workspace)` + `WorkbenchShell`。
- 新类型 `src/types/os.ts`，不覆盖 MCU `Project` / `CapabilityStatus`。
- 新 API 客户端 `src/lib/api/os.ts`；DEMO 走 `src/lib/stores/os-store.ts`（persist），LIVE 走 `/api/os/*`。
- 页面：
  - `/` Today
  - `/start` 原 Start Center
  - `/projects/[id]` Overview / Tasks / Docs / Files / Agents / Activity
  - `/workspace` `/agent` `/debug` 保持 IDE
- Cmd+K 增加 Work OS 命令组，保留 MCU 操作。
- 视觉：现有 dark token、12–13px、无玻璃拟态。

## Backend Architecture

- 仍是 FastAPI `backend/app/main.py`。
- OS 数据在同一 `agent.sqlite`（`backend/app/db.py` + `backend/app/os_store.py`）。
- 路由前缀 `/api/os/`，与 `/api/projects` MCU API 隔离。
- 不启用 leftover SQLAlchemy Gateway。
- SQL 全部参数绑定。凭据只读环境变量。

## Agent Architecture

```
OS Task.assign(c-agent)
  → AgentRun(project_id=backend_project_id, task_id=task.id)
  → 现有 run_agent() / TOOLS / 写保护 / SSE
  → finish → Task.status = review
  → 用户 Approve → Task.status = done
```

planned Agent：`idle|planned|offline`，无 endpoint。

## Data Model

统一状态：

- Project：`planned | active | paused | completed | archived`
- Task：`todo | in_progress | agent_running | review | blocked | done`
- Agent：`idle | running | waiting | error | offline | planned`
- Run：沿用现有 `queued|planning|running|waiting_approval|success|failed|cancelled`

表：`os_projects` `tasks` `task_deps` `documents` `agents` `activities` `os_files`；`runs.task_id` 可空。

firmware 同步：扫描 `workspaces/*/project.json` upsert `os_projects.kind=firmware`。OS 字段不写回 `project.json`。

## Execution Flow

1. 用户创建 OS Project（可挂已有 firmware id）。
2. 创建 Task。
3. Assign Agent：仅 `c-agent` 且项目有 `backend_project_id`。
4. Prompt = task title + description；Context = 现有 `build_context`（IOC > project.json > Board）。
5. UI 订阅 `/api/runs/{id}/events`。
6. 成功 → Needs Review；失败 → Blocked；取消 → In Progress。

## Context System（P0）

P0 不新做检索器。沿用 `backend/app/agent/context.py`。  
P1 再做 Context Pack（Overview / relevant tasks / docs / files / decisions）。

## Automation System（P1 预留）

Trigger / Conditions / Actions。P0 不渲染 Automations tab，避免死按钮。
