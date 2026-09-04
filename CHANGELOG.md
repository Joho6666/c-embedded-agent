# Changelog

## 0.9.0-alpha-mcp — Embedded Engineering Runtime

### Added
- CEA Core façade (`backend/app/core`) shared by Web, MCP, and CLI
- MCP Server v0.1 stdio (`python scripts/cea_mcp.py` / `python -m app.mcp`)
- STM32 Skill Pack under `skills/`
- CLI: `python -m app.cli inspect|build|mcp`
- Docs: ARCHITECTURE, MCP, MCP_TOOLS, SKILLS, HARNESS_INTEGRATION, docs/SECURITY, MIGRATION
- Core / MCP tests; MCP benchmark runner (honest SKIP without LLM)

### Changed
- Product positioning: Embedded Engineering Runtime for AI Coding Agents
- Web build / flash / scan / serial ports / hardware-run call Core
- Unused Universal AI Gateway tree moved to `legacy/universal-ai-gateway/`

### Unchanged
- STM32F103-only production matrix
- Workbench 2.0 / MyOS UI
- Official HAL template and Golden projects
- Honesty rules: no fake Build / Flash / Serial / Hardware PASS

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
