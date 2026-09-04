# Project State

Version target: **0.9.0-beta — IN PROGRESS**. Baseline: `codex/v0.9-multi-platform`.

| Phase | State | Exit evidence |
|---|---|---|
| 0 Audit & Characterization | IMPLEMENTED | Path traversal, permission, API, and hardware characterization tests passing |
| 1 Harness & Governance | IMPLEMENTED | AGENTS.md repository map, docs/INDEX.md, and local/CI quality gates active |
| 2 STM32 Platform Adapter | READY (Beta) | 11/11 Golden projects compile via official CubeF1 HAL with ARM GCC 13.3.1; controlled 3-iteration hardware loop |
| 3 Agent Registries & Routing | IMPLEMENTED | Tool Registry with risk/approval metadata, Skill Registry (STM32 + ESP32), Workflow Router (6 core workflows), Context Router with source tracking |
| 4 Evidence & Release Gates | IMPLEMENTED | `backend/app/release/gates.py` unified gate checker; strict NO FAKE PASS enforcement |
| 5 ESP32-S3 Platform | READY (Beta) | Adapter, template, 7 golden examples (`examples/golden_esp32/`), and CI Docker ESP-IDF 6.1 matrix build active |
| 6 CI & Benchmarks | 6/6 CI GATES PASS | Backend (pytest-asyncio), Frontend (Next.js build), STM32 Golden (11/11), ESP32 Smoke & Matrix (Docker), Quality (secrets + 50 tasks schema + drift check) |
| 7 Hardware Execution | NOT_TESTED | No physical ST-Link probe connected; NO FAKE PASS; honest reporting |

Known limits: hardware and LLM evaluations require external physical and API resources; physical hardware execution requires connected test bench; 8051 roadmap documented in `docs/platforms/8051-roadmap.md`.
