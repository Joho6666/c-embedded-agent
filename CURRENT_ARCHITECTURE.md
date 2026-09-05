# Current Architecture Audit

Audit baseline: `main@db3279164048b12ad08eba1e533de5297f3bdf21`.

## Runtime and call flow

The v0.8 flow is `FastAPI -> runtime.py -> planner/context/tools -> STM32F103 compiler, generator, OpenOCD, serial and validators`. `runtime.py` owns lifecycle, SSE, approvals, tool declarations and dispatch, compilation, validation, hardware and the LLM loop. The target flow moves routing and platform execution behind registries while retaining one runtime.

## Hard-coded boundaries

- Context truncates the project tree to 80 and relevant core files to 24; knowledge retrieval is similarly fixed rather than budgeted by task.
- Tool declarations and dispatch are separate structures. Peripheral `configure_*` calls and mechanical fixes are not governed by one effect/approval policy.
- Planner, skills and validators are STM32F1 keyword based; board defaults include Blue Pill, PC13, PA9/PA10, ARM GCC and OpenOCD F1 configuration.
- Hardware execution and validation are coupled to local STM32 tooling. Missing devices must remain non-PASS.

## Public surface and frontend coupling

The existing API exposes projects, IOC analysis/import, existing-tree scan/import, files, build/artifacts, flash, serial, hardware, validation, runs/SSE, skills, knowledge, error memory and benchmark data. The v0.8 new-project UI lists unsupported families, but the LIVE Agent store creates a fixed STM32F103 project. Existing import endpoints exist but the UI reports them unavailable. Flash uses HTTP success rather than operation evidence.

## Tests, CI and evidence

- Baseline contains 67 backend tests across 27 files and 11 committed STM32F103 Golden projects.
- CI only builds the frontend and runs backend pytest. ARM compilation is skipped when its toolchain is absent.
- There are 20 benchmark prompts, but committed summaries record zero executed LLM tasks because no LLM was configured.
- Hardware validation was not run. Release evidence must say `NOT RUN`/`UNAVAILABLE`, not PASS.
