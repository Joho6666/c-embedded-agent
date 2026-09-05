# Project State

Version target: **0.9.1-beta — IN PROGRESS**. Baseline: `codex/v0.9-multi-platform`.

| Phase | State | Exit evidence |
|---|---|---|
| 0 Audit & Characterization | IMPLEMENTED | Path traversal, permission, API, and hardware characterization tests passing |
| 1 Harness & Governance | IMPLEMENTED | AGENTS.md repository map, docs/INDEX.md, and local/CI quality gates active |
| 2 STM32 Platform Adapter | READY (Beta) | 11/11 Golden projects compile via official CubeF1 HAL with ARM GCC 13.3.1; controlled hardware loop |
| 3 Agent Registries & Routing | IMPLEMENTED | Tool Registry with idempotency/resume policy/approval metadata, Skill Registry (STM32 + ESP32), Workflow Router (6 core workflows), Context Router with token budget telemetry |
| 4 Evidence & Release Gates | IMPLEMENTED | `backend/app/release/gates.py` unified gate checker; strict NO FAKE PASS enforcement |
| 5 ESP32-S3 Platform | READY (Beta) | Adapter, template, 7 golden examples (`examples/golden_esp32/`), and CI Docker ESP-IDF 6.1 matrix build active |
| 6 8051 SDCC Platform | COMPILE VERIFIED | Adapter, template, 4 golden examples (`examples/golden_8051/`), and CI SDCC build job active |
| 7 CI & Benchmarks | 7/7 CI GATES PASS | Backend (pytest-asyncio), Frontend, STM32 Golden (11/11), ESP32 Smoke & Matrix (Docker), 8051 Golden (SDCC), Quality (secrets + 50 tasks schema + drift check) |
| 8 Crash Resume | IMPLEMENTED | Phase-aware resume across plan, reasoning, tool_call, compile, flash; idempotent replay protection; crash injection tests green |
| 9 Hardware Execution | NOT_TESTED | No physical ST-Link probe connected; NO FAKE PASS; WAITING_FOR_USER human-in-the-loop state interface |

Known limits: physical hardware execution requires connected test bench; LLM evaluations require external API credentials.
