# Changelog

## Unreleased — MyOS P0 overlay

Added a Work OS layer on C-Agent Workbench 2.0 without replacing firmware execution.

### Added
- `MYOS_AUDIT.md`, `MYOS_ARCHITECTURE_V2.md`
- SQLite OS tables: projects, tasks, documents, agents, activities
- `/api/os/*` CRUD, Today, Assign Agent (C-Agent only), Review
- Today at `/`; Start Center moved to `/start`
- Project detail tabs: Overview / Tasks / Docs / Files / Agents / Activity
- Task Assign Agent + Review (Approve / Request changes / Retry / Reject)
- Cmd+K commands: Create project, Create task, Open Today, Open C-Agent
- Agent registry seed: C-Agent runnable; Codex / Claude Code / Grok / Custom planned

### Unchanged
- STM32F103 Support Matrix
- Agent runtime tools, write protection, Stop, SSE
- `/workspace` `/debug` `/build` hardware pipeline

### Next (P1)
- Agents Control Center
- Automation (Trigger / Conditions / Actions)
- Context Pack retrieval
- Inbox as a first-class page
- Project memory precipitation
