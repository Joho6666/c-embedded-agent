# Project State

Version target: **0.9.0-beta — IN PROGRESS**. Baseline: `db3279164048b12ad08eba1e533de5297f3bdf21`.

| Phase | State | Exit evidence |
|---|---|---|
| 0 Audit/characterization | IMPLEMENTED | Audit plus path, permission, API and hardware characterization tests |
| 1 Harness | IMPLEMENTED | Governance docs and local gates present |
| 2 STM32 adapter | IMPLEMENTED | Runtime/API/workspace delegate through `stm32f103-hal` |
| 3 Agent registries/routers | IMPLEMENTED | Tool, workflow, skill and budgeted context routing integrated |
| 4 STM32 gate | PASS (local) | 130 passed, 1 OS symlink skip; frontend build PASS; 11/11 ARM GCC 13.3 Golden PASS |
| 5 ESP32-S3 | EXPERIMENTAL | Minimal adapter/template implemented; local ESP-IDF smoke SKIPPED because Docker daemon/ESP-IDF unavailable |
| 6 CI/benchmark | IMPLEMENTED / EVAL SKIPPED | Five CI jobs and 50 tasks; LLM benchmark remains SKIPPED without credentials |

Known limits: run checkpoint/restart is out of scope; hardware and LLM evaluations require external resources; ESP32-S3 remains experimental pending the ESP-IDF 6.1 CI smoke; no other platform may be advertised as supported. Version files remain 0.8.0-beta until every release gate has evidence.
