# Harness integration

## Launch (confirmed)

```
python scripts/cea_mcp.py
```

stdio JSON-RPC MCP. Working directory = repository root. `backend/` must be importable (`scripts/cea_mcp.py` puts it on `sys.path`).

## Claude Code

Example: `.mcp.json` (also `examples/harness/claude-code.mcp.json`).

Point Skills at `skills/*/SKILL.md`.

Status of end-to-end Claude Code UI enablement on this machine: **UNTESTED** unless a later report says otherwise. The config file matches current Claude Code `mcpServers` practice.

## Cursor

Example: `.cursor/mcp.json` and `.cursor/rules/cea-stm32.md`.

Status: **UNTESTED** on this machine (config provided, not clicked through).

## Codex

No verified Codex MCP file format in this repo. Stdio command is the interface. Status: **UNTESTED**.

## OpenCode

Same: stdio only. Status: **UNTESTED**.

Do not read “example JSON exists” as “Supported”.
