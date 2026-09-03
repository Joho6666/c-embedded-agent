# Repository Guide

- Read `PROJECT_STATE.md` and `ARCHITECTURE.md` before changing behavior.
- Preserve existing REST URLs and tool names. New platforms must enter through a registered adapter; never silently fall back to STM32F103.
- Treat workspace writes and all device operations as security boundaries. Path containment cannot be bypassed by mode.
- A passing claim requires recorded evidence. Missing LLMs, toolchains, probes, boards, or serial ports are `SKIPPED`, `NOT RUN`, or `UNAVAILABLE`, never zero-scored success.
- Run `python scripts/pre_finish.py` before handoff. Do not update release status to v0.9 complete until every gate in `PROJECT_STATE.md` passes.
