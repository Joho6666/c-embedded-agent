# Generic CEA MCP stdio

Command (from repository root):

```
python scripts/cea_mcp.py
```

Equivalent:

```
python -m app.mcp
```

(run with `backend/` on `PYTHONPATH` or `cd backend`.)

Transport: **stdio** (JSON-RPC MCP).

This is the only confirmed launch interface. Codex / OpenCode config file formats are **UNTESTED** — do not invent client-specific JSON. Point those clients at the stdio command above if they accept a raw MCP stdio server.
