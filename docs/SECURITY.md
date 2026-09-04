# CEA Core / MCP security

Root `SECURITY.md` is a leftover Universal AI Gateway checklist. This file is the product security model for v0.9.0-alpha-mcp.

## Side effects

- READ_ONLY: inspect, IOC, pins, board, diagnose, list_serial_ports, read_serial
- MUTATING: build (artifacts), configure_peripheral (Core/Src codegen)
- HARDWARE_ACTION: flash_firmware, validate_hardware

Hardware tools require `confirm=true`.

## Path

- `project_root` is resolved and must be a directory.
- Optional `CEA_ALLOWED_ROOTS` (comma-separated prefixes).
- Relative paths cannot escape the project root (`resolve_in_root`).
- Writes still use `assert_writable`: Drivers/, Middlewares/, startup*, *.ld, Makefile, *.ioc are protected.

## Execution

- No arbitrary shell tool.
- OpenOCD argv is fixed (`interface/stlink.cfg`, `target/stm32f1x.cfg`).
- Flash attempts are capped per process (default 8).
- LLM URL policy (public http/https only) is unchanged in `app/net.py`.
