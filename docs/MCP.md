# CEA MCP Server v0.1

Local **stdio** MCP server. Not a cloud MCP. CEA must see ARM GCC, make, OpenOCD, USB, serial, and the STM32 tree.

## Start

From repository root:

```bash
pip install -r backend/requirements.txt
python scripts/cea_mcp.py
```

From `backend/`:

```bash
python -m app.mcp
```

CLI:

```bash
cd backend && python -m app.cli mcp
```

## Client snippets

Claude Code / Cursor: see `examples/harness/` and repo `.mcp.json` / `.cursor/mcp.json`.

Codex / OpenCode: **UNTESTED**. Use the stdio command above if the client accepts a raw MCP stdio server. Do not assume a file format we have not run.

## Contract

- Every tool returns JSON with `status` and `side_effect`.
- Exceptions become `FAIL`, never `PASS`.
- `flash_firmware` and `validate_hardware` require `confirm=true`.
- Tools call CEA Core only.
