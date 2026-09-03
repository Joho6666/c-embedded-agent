# Project State

Version target: **0.9.0-beta — IN PROGRESS**. Baseline: `db3279164048b12ad08eba1e533de5297f3bdf21`.

| Phase | State | Exit evidence |
|---|---|---|
| 0 Audit/characterization | IN PROGRESS | Audit recorded; security characterization must pass |
| 1 Harness | IMPLEMENTED | Governance docs and local gates present |
| 2 STM32 adapter | IN PROGRESS | Adapter contract and regression suite required |
| 3 Agent registries/routers | IN PROGRESS | Permission, routing, context and skill tests required |
| 4 STM32 gate | NOT RUN | Python 3.11, Node 20, ARM GCC 13.3 and 11 Golden builds |
| 5 ESP32-S3 | DEFERRED UNTIL PHASE 4 | ESP-IDF 6.1 smoke; hardware may be SKIPPED |
| 6 CI/benchmark | IN PROGRESS | Five CI jobs and at least 50 task definitions |

Known limits: run checkpoint/restart is out of scope; hardware and LLM evaluations require external resources; no platform beyond registered adapters may be advertised as supported.
