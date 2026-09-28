# cea-embedded: plug the workbench into your own agent

`cea-embedded` is an MCP server plus skills. Install it into Claude Code, Codex, Cursor or any
MCP client and your agent can build firmware, flash it with one call, and see the board's
latest state — without leaving the chat.

```
your harness (Claude Code / Codex / Cursor)
      │ MCP stdio
      ▼
cea-embedded MCP server ──── skills (SKILL.md)
      │
      ▼
DeviceService (session: serial history, last build/flash, pins)
      │  one backend contract
 ┌────┴──────────────┐
 ▼                   ▼
virtual Blue Pill    real STM32F103 via ST-Link + USB-serial
(Renode)             (NOT YET VALIDATED on hardware)
```

## Tools

| Tool | What it does |
|---|---|
| `doctor` | Toolchain, Renode, OpenOCD, serial ports, active backend |
| `build` | `make`; errors with file/line, warnings, flash/RAM usage |
| `flash` | **One click:** build → flash → run → capture serial; optional `expect` text |
| `status` | **Latest state:** backend + evidence kind, firmware hash, last build/flash, recent serial, PC13/LED |
| `serial_read` / `serial_write` | Tail the running firmware's UART (incremental via `since_seq`), send console input |
| `read_pins` | GPIO output/input levels now |
| `verify_behavior` | Deterministic timing/output assertions in a fresh simulation (LED periods ±5 %, UART text) |
| `pin_check` | Pins already claimed by the project, conflicts |

Every result is labelled `SIMULATED` (virtual board) or `HARDWARE` (real probe). The server's
instructions tell the model never to claim firmware works without a tool result.

## Backend selection

`CEA_DEVICE=auto` (default) uses a real board when OpenOCD sees an STM32F1 through an ST-Link,
otherwise the virtual Blue Pill. Force with `CEA_DEVICE=virtual` or `CEA_DEVICE=hardware`;
set the serial port with `CEA_SERIAL_PORT=COM5`.

The virtual board is one long-lived Renode process: reflashing does not restart it, serial output
streams continuously, and virtual time advances in the background (slower than wall time on most
machines — `status.device.virtual_time_s` shows it). First start takes ~20 s.

## Requirements

- Python 3.11 with `pip install -r backend/requirements.txt` (includes `mcp<2`; the server uses the 1.x `FastMCP` API)
- `arm-none-eabi-gcc` + `make` on PATH (or `~/tools/xpack-*`, or `CEA_TOOLCHAIN_PATH`)
- Virtual board: [Renode](https://github.com/renode/renode) (`CEA_RENODE_PATH` or `~/tools/renode*`);
  `verify_behavior` also needs `robotframework==6.1 psutil pyyaml` (`CEA_RENODE_PYTHON` or `~/tools/renode-venv`)
- Real board: OpenOCD + ST-Link, and a USB-serial adapter on USART1

## Install

Set `CEA_HOME` to this repository's path (used by the plugin's `.mcp.json`).

**Claude Code** — as a plugin (MCP server + skills):

```bash
claude plugin install /path/to/c-embedded-agent/plugin
```

or only the MCP server:

```bash
claude mcp add cea-embedded -- python /path/to/c-embedded-agent/scripts/cea_mcp.py
```

**Codex** — `~/.codex/config.toml`:

```toml
[mcp_servers.cea-embedded]
command = "python"
args = ["/path/to/c-embedded-agent/scripts/cea_mcp.py"]
tool_timeout_sec = 300
startup_timeout_sec = 60
# Non-interactive `codex exec` uses approval_policy = "never", which rejects every
# MCP call that would need approval. Pre-approve this server's tools:
default_tools_approval_mode = "approve"
```

Copy `plugin/skills/*` into `~/.codex/skills/` to use the skills.

**Cursor** — `.cursor/mcp.json`:

```json
{ "mcpServers": { "cea-embedded": { "command": "python", "args": ["/path/to/c-embedded-agent/scripts/cea_mcp.py"] } } }
```

## Skills

| Skill | Use |
|---|---|
| `embedded-flash-verify` | The edit → flash (expect) → status → verify_behavior loop and evidence rules |
| `stm32f1-bluepill-pitfalls` | Active-low LED, `_write` in `syscalls.c`, USART pins, clocks, IRQ names |
| `embedded-no-output-triage` | "Flashed but nothing happens" — layer-by-layer triage |

## Status

The virtual path is tested end to end (unit tests, MCP stdio tests, and a real harness run).
The hardware backend reuses the same contract but has not been run on a physical board yet;
`status.device.validated` is `false` for it.
