# Migration 0.8.0-beta → 0.9.0-alpha-mcp

## What changed

- Product shape: STM32 AI Web App → Embedded Engineering Runtime (MCP + Core + Web).
- New `backend/app/core/` is the façade. Implementations remain `app.tools.*`.
- Web build/flash/scan/serial-ports/hardware-run call Core. HTTP JSON kept compatible.
- MCP stdio server: `python scripts/cea_mcp.py`.
- CLI: `python -m app.cli inspect|build|mcp`.
- Unused Universal AI Gateway Python tree moved to `legacy/universal-ai-gateway/`.

## What did not change

- STM32F103-only execution.
- Workbench 2.0 / MyOS UI.
- Official HAL template and Golden projects.
- Agent runtime tool loop (still uses `app.tools` directly).
- `unigateway/` leftover console (still not product).

## Compatibility

Existing `/api/projects/{id}/build` still returns compiler `success/exit_code/artifacts`. Extra Core fields are not required by the UI.

## Env

- `CEA_TOOLCHAIN_PATH` — unchanged
- `CEA_ALLOWED_ROOTS` — optional MCP/Core project-root allowlist
