# MCP Tools

| Tool | Side effect | Core | Notes |
|---|---|---|---|
| inspect_project | READ_ONLY | yes | Platform, MCU, board, IOC, toolchain |
| parse_ioc | READ_ONLY | yes | Missing fields null |
| check_pin_conflicts | READ_ONLY | yes | PASS / WARNING / FAIL / UNKNOWN + evidence |
| get_board_context | READ_ONLY | yes | IOC > project.json > Board Profile > Default |
| build_project | MUTATING | yes | Artifacts only. No gcc → UNAVAILABLE. No ELF → FAIL |
| diagnose_build | READ_ONLY | yes | gcc/ld + Error Memory. Does not compile |
| flash_firmware | HARDWARE_ACTION | yes | confirm=true. OpenOCD ST-Link. Rate-limited |
| list_serial_ports | READ_ONLY | yes | port / description / hwid |
| read_serial | READ_ONLY | yes | Real bytes only |
| validate_hardware | HARDWARE_ACTION | yes | confirm=true. No board ≠ PASS |
| configure_peripheral | MUTATING | yes | Existing periph_gen. Pin conflict refuses unless force |

No arbitrary shell. No unrestricted filesystem. Protected: Drivers/, startup*, *.ld, Makefile, *.ioc.
