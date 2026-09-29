# RELEASE_REPORT — C-Embedded Agent 0.10.0-beta

Evidence-Driven Embedded Engineering Harness. Every number below was measured
on this machine during the v0.10 run (see `RELEASE_EVIDENCE.json`,
`docs/CURRENT_STATE.md`, `docs/RENODE_SPIKE.md`).

## Version

- App / Agent Runtime / Template: **0.10.0-beta** (VERSION, CHANGELOG, README, package.json agree — guarded by `scripts/check_docs_drift.py`)
- STM32CubeF1 HAL: 1.1.9 (`vendor.lock.json`)
- Status: **Engineering Beta (early)** — see tier justification at the end

## Baseline → v0.10 test results (real runs)

| Suite | v0.9 baseline (2026-09-05) | v0.10 (2026-09-06) |
|---|---|---|
| backend pytest | 110 passed / 1 skipped | **208 passed / 1 skipped** (+98 tests) |
| frontend lint / vitest / build | clean / 23 / OK | **clean / 23 / OK** |
| golden builds | 11/11 (sizes recorded) | 11/11 (artifact analyzer now derives sections/budgets) |

Skips remain honest: symlink-privilege test (Windows), benchmark LLM path, simulation test absent-Renode.

## What v0.10 adds (all code-pathed + unit-tested; evidence marked where real)

### Hardware Lab (P0)
- `HardwareDevice` model with honest statuses; USB VID/PID discovery (ST-Link/J-Link/CMSIS-DAP/ESP/CH340/CP210x/FTDI) and a Hardware Discovery Report — **fuzzy USB hints never claim an MCU**; registry live-probed on this machine (CH340 on COM7 ONLINE, ST-Link absent → `not_installed`).
- `hardware-map.yaml` inventory (Twister-inspired; `requiredDevices[]` schema for future multi-DUT).
- `HardwareRun` records: firmware/ELF sha256 + git commit + toolchain + flash/reset/serial + evidence; **PASS gate refuses PASS without flash success + real hardware evidence**; every hardware run persists a replayable record.

### Debug layer
- `DebugProbeAdapter` (OpenOCD SUPPORTED path; pyOCD/J-Link declared NOT_SUPPORTED until tested), read-only register/memory allowlists (SCB + RM0008).
- GDB/MI `DebuggerSession` — machine-interface only (no terminal scraping): breakpoints, run/step/continue, registers, memory, expression eval, backtrace. Protocol-tested with a scripted MI responder; real-gdb smoke test. **Live hardware debug sessions: NOT_TESTED** (OpenOCD absent on this machine).
- CrashEvidence: CFSR/HFSR/MMFAR/BFAR/PC/SP decoded to concrete causes (null-pointer write, peripheral clock not enabled, stack overflow, INVSTATE…).
- Debugger workflow endpoint: build → flash → reset → serial → halt → fault decode (`/api/hardware/debugger/diagnose`).

### Evidence model
- `EvidenceRecord` + three-level `VerificationReport`: **Build PASS ≠ Simulation PASS ≠ Hardware PASS**; FAIL anywhere → FAIL; overall PASS requires HARDWARE+BUILD; otherwise PARTIAL. Per-peripheral evidence requirements (LED needs observed toggle, USART needs the token really received, GPIO-input needs an actual signal change — code inspection is evidence nowhere).
- Human-in-the-loop `WAITING_FOR_USER` request/confirm records; `DANGEROUS_HARDWARE` policy (mass erase / option bytes / flash protection / bootloader overwrite BLOCKED by default, single-use approval token); PowerControllerAdapter is interface-only.

### Simulation (real result)
- **Renode 1.15.3 spike: SUPPORTED for STM32F103.** Our own STM32F103 ELF (135 B text, ARM GCC 13.3.1) ran headless in Renode's `stm32f103.repl` and emitted `CEA:SIM:PASS` through the UART file backend. Verified again inside pytest (`test_renode_real_spike_stm32f103`). First run also surfaced a real behavioral rule: Renode drops UART chars until CR1 `UE|TE` are set — simulation catches sloppy init like hardware does.
- ESP32 spike: **NOT_RUN** (ESP-IDF/esptool absent — documented in `docs/ESP32_SIM_SPIKE.md` with the upgrade path).

### Benchmark v2
- **50 tasks** (20 regression + 30 capability) across PERIPHERAL_CONFIG / COMPILE_REPAIR / SAFETY / DEBUGGING / LONG_HORIZON / CONTEXT; repair & debugging tasks carry deterministic injected faults; per-domain + regression/capability rates recorded.
- **Agent vs Baseline: implemented, not run** — no LLM configured here; `comparison-summary.json` records `LLM not configured — not faking Agent vs Baseline`. Multi-trial pass@1 lands with the first configured LLM.
- Outcome Memory (SQLite): per-run attempts/tokens/time + build/simulation/hardware success, wired into the benchmark and the hardware pipeline. This is the Router's future input.
- Error Memory v2: platform/toolchain/phase/error_class + verified/failed/**hardwareVerified** counters — hardwareVerified only rises with real hardware evidence.

### Platform v2 & planning
- Evidence-derived capability matrix (`GET /api/platforms`) — this host: BUILD **VERIFIED**, SIMULATE **VERIFIED** (Renode run), FLASH/DEBUG/SERIAL/HARDWARE_VALIDATE **UNVERIFIED** (code-complete, no live hardware evidence), ESP32/C51/RP2040/Host-C **NOT_SUPPORTED**.
- ContextManifest: every context entry records source/reason/priority/tokens/hash.
- ActionPlan: steps carry action/tool/permission/expectedEvidence/retryPolicy; deterministic ops stay Tools.
- Unified approval policy (`GET /api/approvals/policy`).

### Artifact intelligence
- ELF section analysis, largest symbols (`nm --size-sort`), flash/RAM budget gates (project budgets else C8T6 64K/20K; >100% FAIL, >90% WARNING) — `/api/projects/{id}/artifacts/analysis`.
- `FirmwareChangeReport`: flash/RAM deltas, per-section deltas, new/removed symbols, risk notes.
- Embedded lint (`/api/projects/{id}/lint`): ISR blocking/unsafe calls → ERROR (blocking); unsafe string fns, stack-heavy arrays, missing-volatile, busy-wait → WARNING/INFO (advisory). Zero LLM involvement.

### CI layering
- L1 fast: frontend lint/test/build + pytest + docs-drift + secret-scan.
- L2 toolchain: apt ARM GCC → all goldens + benchmark smoke (asserts no fake scores).
- L3 simulation: pinned Renode install → real simulation tests.
- L4 hardware: self-hosted `hardware` runner, `workflow_dispatch` only — cloud runners never pretend.

### UI
- Hardware Lab page: devices, discovery report, planned inventory; honest statuses only.
- Run Inspector (`/history/[runId]`): execution trace (plan → LLM → tools → compile → hardware) + firmware budget panel.

### Docs & cleanup
- `docs/CURRENT_STATE.md` (audit), `docs/hardware-lab/stm32f103-bluepill.md` (reproducible fixture), `docs/RENODE_SPIKE.md`, `docs/ESP32_SIM_SPIKE.md`, rewritten `RELEASE_REPORT.md`, drift gate + secret scan in CI.
- Removed `unigateway/` graft + dead gateway tests; `mcp` pinned `<2` (v2.1.1 had broken the MCP server).

## Benchmark

`python benchmarks/benchmark.py` → honest SKIP: `LLM not configured`, `template_build: true`. 20 existing tasks preserved, 30 added. `domainRates`/`levelRates` fill when an LLM is configured.

## Hardware

**Hardware Execution: NOT_TESTED** on this machine (no ST-Link/OpenOCD). CH340 on COM7 discovered and registered. All hardware paths return UNAVAILABLE with reasons; nothing pretends.

## Phase J — next-platform recommendation (scoring, no new adapters this round)

Criteria weights: user volume, ecosystem, toolchain stability, architecture reuse with STM32 adapter, testability, commercial value.

| Candidate | User volume | Ecosystem | Toolchain | Adapter reuse | Testability | Verdict |
|---|---|---|---|---|---|---|
| **STM32F4** | high | high | same arm-gcc/make | **very high** (same HAL patterns, CubeF4 vendoring reuses `sync_cubef1.py` model) | high (Renode has F4 boards) | **recommended next** |
| RP2040 | high | high | same gcc + cmake/picosdk | medium (SDK ≠ HAL; PIO complexity) | high (Renode/micropython-friendly) | second |
| Zephyr | growing | large | west/CMake (new pipeline) | low (build layer differs entirely) | high (Twister + hardware map native) | third — big win, bigger lift |
| nRF52 | medium | medium | same gcc + softdevice quirks | medium | medium | not now |

**Recommendation: STM32F4** after the hardware lab is proven — the PlatformAdapter v2 shape, capability matrix and board profiles were designed so F4 is a data + vendoring change, not a runtime rewrite.

## Release gate (brief §60) — status

- STM32F103 real hardware (flash/serial/≥5 peripheral tests): **NOT MET** — needs the physical lab (fixture doc delivered).
- Real Agent run + Agent vs Baseline: **NOT MET** — needs LLM config (harness ready).
- Simulation feasibility spike: **MET** (Renode SUPPORTED, real run).
- Debugger connect/halt/read/resume: **PARTIAL** — GDB/MI + probe adapters built and protocol-tested; live session needs OpenOCD+probe.
- Hardware session replayable: **MET** (HardwareRun records with hashes; pipeline persists them).
- Documentation consistent: **MET** (drift gate green).

## Known limitations

- Hardware loop unproven on real boards until a probe is attached (fixture doc + honest UNAVAILABLE until then).
- Agent vs Baseline and pass@1 statistics require a configured LLM.
- Renode spike covers UART + core execution for F103; PWM/I2C/SPI simulation validators are future work.
- `mcp` remains on the v1 API (pin `<2`); migration to mcp 2.x tracked as tech debt.
- Code-mode approval is still in-process; the new policy surface is declarative but the runtime enforcement upgrade lands with the approval-engine integration.

## Tier (evidence-based)

**Engineering Beta (early).** Rationale: multi-surface engineering harness with a real evidence model, real simulation proof, layered CI and honest degradation — but zero live-hardware sessions recorded and zero real benchmark runs. The gate to "Engineering Beta (confirmed)" is exactly the remaining §60 hardware items.
