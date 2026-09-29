# Changelog

## 0.10.0-beta — Evidence-Driven Embedded Engineering Harness

### Added — Hardware Lab (P0)
- `backend/app/hardware/` — HardwareDevice model (honest ONLINE/OFFLINE/BUSY/UNKNOWN/FAULT; MCU stays UNKNOWN until SWD chip-id evidence), USB VID/PID discovery (ST-Link/J-Link/CMSIS-DAP/ESP/CH340/CP210x/FTDI table), Hardware Discovery Report, `hardware-map.yaml` inventory (Twister-inspired, `requiredDevices` ready), persistent device registry
- HardwareRun records: sha256(firmware/ELF) + git commit + toolchain + flash/reset/serial/evidence, PASS gate refuses hardware PASS without flash success + real hardware evidence; every `/api/hardware/run` now persists a replayable run

### Added — Debug & Probe layer
- DebugProbeAdapter abstraction: OpenOCDAdapter (SUPPORTED path) with read-only register/memory allowlists (SCB + RM0008 STM32F1 map); pyOCD/J-Link registered NOT_SUPPORTED until really tested
- GDB/MI DebuggerSession (`gdb -i=mi`, queue-based async MI parser): breakpoints, run/step/continue, registers, memory, expression eval, backtrace; protocol-tested against a scripted responder + real-gdb smoke
- CrashEvidence: CFSR/HFSR/MMFAR/BFAR/PC/SP decoder with concrete possible causes (null-pointer write, missing RCC clock, stack overflow, INVSTATE…)
- Debugger workflow `/api/hardware/debugger/diagnose`: build → flash → reset → serial → halt → fault decode

### Added — Evidence & Simulation
- EvidenceRecord model + three-level VerificationReport (Build ≠ Simulation ≠ Hardware; FAIL anywhere → FAIL; overall PASS needs HARDWARE+BUILD; otherwise PARTIAL)
- Peripheral evidence requirements (LED/PWM/USART/ADC/I2C/SPI/EXTI/GPIO-input) — compile success is evidence nowhere
- SimulationAdapter + RenodeAdapter — **real Renode 1.15.3 run: STM32F103 ELF emitted CEA:SIM:PASS via UART file backend** (`docs/RENODE_SPIKE.md`, verdict SUPPORTED); ESP32 spike honestly NOT_RUN (`docs/ESP32_SIM_SPIKE.md`)
- Human-in-the-loop WAITING_FOR_USER requests/confirmations; DANGEROUS_HARDWARE policy (mass erase/option bytes/bootloader BLOCKED by default, single-use token); PowerControllerAdapter interface-only

### Added — Benchmark v2 & Memory
- 50 tasks (20 regression + 30 capability) across PERIPHERAL_CONFIG / COMPILE_REPAIR / SAFETY / DEBUGGING / LONG_HORIZON / CONTEXT with injected faults for repair/debug tasks; per-domain + regression/capability rates in results
- OutcomeMemory (SQLite): per-run attempts/tokens/time + build/simulation/hardware success; wired into benchmark + hardware pipeline
- Error Memory v2: platform/toolchain/phase/error_class columns, verified/failed/hardwareVerified counters (hardwareVerified only rises with real hardware evidence)

### Added — Platform v2 & planning
- Evidence-derived capability matrix `/api/platforms` (VERIFIED/UNVERIFIED/NOT_SUPPORTED per host); unified approval policy `/api/approvals/policy`
- ContextManifest (per-entry source/reason/priority/tokens/hash); ActionPlan steps carry action/tool/permission/expectedEvidence/retryPolicy

### Added — Artifact intelligence & CI
- Artifact analysis: ELF sections, largest symbols, flash/RAM budget gates (per-project budgets, MCU defaults), FirmwareChangeReport (deltas + symbol movement + risk notes) at `/api/projects/{id}/artifacts/analysis`
- Embedded lint: ISR blocking/unsafe calls (ERROR), unsafe string fns, stack-heavy arrays, missing-volatile, busy-wait → StaticFinding with ERROR/WARNING/INFO; `/api/projects/{id}/lint`
- CI layered: L1 fast (lint/test/pytest/docs-drift/secret-scan) → L2 toolchain (goldens + benchmark smoke) → L3 simulation (Renode) → L4 hardware (self-hosted, manual dispatch only)
- `scripts/gen_release_evidence.py` → RELEASE_EVIDENCE.json (measured, not hand-written)

### UI
- Hardware Lab page (devices, discovery report, map); Run Inspector (`/history/[runId]`) with execution trace + firmware budget panel

### Fixed
- `mcp` pinned `<2` (v2.1.1 removed FastMCP and broke the MCP server)

### Removed
- `unigateway/` graft and dead gateway tests (zero runtime references; history preserved)

## Unreleased — v0.10.0-beta Phase A (Audit + Hardware Truth)

### Fixed
- `mcp` dependency pinned `<2` (pip resolved 2.1.1 which removed `FastMCP`; MCP server targets the v1 API). Venv downgraded to 1.29.1, MCP tests 5/5 again.
- `RELEASE_REPORT.md` regenerated from the real 2026-09-05 baseline (was stale at 0.8.0-beta with old test counts).

### Added
- `docs/CURRENT_STATE.md` — evidence-based audit: implemented / verified / compile-only / not verified / experimental / debt / drift.
- `scripts/check_docs_drift.py` + `scripts/secret_scan.py` — Layer-1 CI gates, wired into GitHub Actions.
- Real baseline recorded: pytest 110 passed / 1 skipped, frontend lint+vitest 23/23+build green, 11/11 golden builds with sizes, benchmark honest SKIP (LLM not configured), hardware NOT_TESTED (no probe on this machine).

### Removed
- `unigateway/` graft (97 tracked files, zero runtime references; history preserved).
- Dead `backend/tests/test_gateway.py` + `test_v090.py` (imported deleted `app.gateway.*` / `app.models.database` / `app.core.limiter`); `pytest.ini` ignores dropped.

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
