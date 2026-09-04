# CEA Architecture

Version: **0.9.0-alpha-mcp**

C-Embedded Agent is an **Embedded Engineering Runtime** for AI coding agents. Harnesses reason and edit source. CEA performs real embedded engineering.

```
Harness (Codex / Claude Code / Cursor / OpenCode)
   │
   ↓
CEA MCP (stdio)     CLI (`python -m app.cli`)     Web UI
   │                      │                          │
   └──────────────────────┼──────────────────────────┘
                          ↓
                      CEA Core
                          │
          ┌───────────────┼────────────────┐
          │               │                │
        Build           Flash            Serial
          │               │                │
         IOC            Board             MCU
          │               │                │
      Validation      Error Memory     STM32Adapter
```

## Layers

| Layer | Role |
|---|---|
| Harness | Plan, edit `Core/Src`, decide next step |
| MCP / CLI / Web API | Transport only |
| **CEA Core** | The only capability implementation façade |
| `app.tools.*` / `validation` / `mcu` | Existing real implementations Core delegates to |
| Host tools | ARM GCC, make, OpenOCD, ST-Link, pyserial |

Web API and MCP **must not** reimplement `make` / OpenOCD / IOC parsing.

## Core APIs

`inspect_project` · `parse_ioc` · `check_pin_conflicts` · `get_board_context` · `build_project` · `diagnose_build` · `flash_firmware` · `list_serial_ports` · `read_serial` · `validate_hardware` · `configure_peripheral`

## Platform adapter

`PlatformAdapter` Protocol with a single implementation: `STM32Adapter` (STM32F103). No empty ESP32/C51 adapters.

## Honesty

Missing toolchain → `UNAVAILABLE`. Missing ELF after make 0 → `FAIL`. No board → hardware `UNAVAILABLE` / `UNKNOWN` / `PARTIAL`, never `PASS`.
