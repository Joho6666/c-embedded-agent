# RELEASE_REPORT — C-Embedded Agent 0.8.0-beta

> v0.9.0-beta architecture work is IN PROGRESS. This report remains the last release report and must not be read as v0.9 completion evidence.

Current v0.9 gate evidence is maintained separately in `docs/V09_VERIFICATION.md`; it does not promote the released version.

## Version

- App: 0.8.0-beta
- Agent Runtime: 0.8.0-beta
- Template: `templates/stm32f103_hal_official`
- STM32CubeF1 HAL: 1.1.9 (`__STM32F1xx_HAL_VERSION` in `stm32f1xx_hal.c`)
- Status: **Late Beta** — not Production Candidate

Production Candidate requires: Backend+Frontend CI green, ≥30 benchmark tasks, Final Compile ≥90%, Semantic ≥85%, Auto Fix ≥80%, Agent clearly beating Baseline, and hardware evidence. This release does **not** meet the benchmark/hardware bars.

## CI

### Frontend

PASS — `npm run build` (Next.js 15.5.24 Turbopack) succeeded on this machine.

### Backend

PASS — `cd backend && python -m pytest -q`

- 64 passed, 1 skipped (`test_symlink_escape`: Windows symlink privilege not available)
- Gateway leftovers `tests/test_gateway.py` and `tests/test_v090.py` are ignored via `pytest.ini`. They test Universal AI Gateway `/v1`/`/admin`, which this FastAPI app does not mount. Agent tests were not deleted to manufacture green.

## Benchmark

Command: `python benchmarks/benchmark.py`

Environment:

- `arm-none-eabi-gcc`: present (`~/tools/xpack-arm-none-eabi-gcc-13.3.1-1.1`)
- `make`: present (`~/tools/xpack-windows-build-tools-4.4.1-3`)
- LLM (`LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`): **not configured**

Result (`benchmarks/stm32f103/latest-summary.json`):

- Tasks: 0 (harness skipped; 20 task JSON files exist)
- First Build: 0.0 (not run)
- Final Compile: 0.0 (not run)
- Auto Fix: 0.0 (not run)
- Semantic Validation: 0.0 (not run)
- Avg Iterations: 0.0
- Avg Latency / tokens: 0
- skipped: `LLM not configured`
- Official HAL template compile: **true** (`template_build`)

No fake task scores were written.

## Agent vs Baseline

`benchmarks/comparison-summary.json`:

```json
{
  "skipped": ["LLM not configured"],
  "reason": "LLM not configured — not faking Agent vs Baseline"
}
```

Baseline Compile Success: not measured  
Agent Compile Success: not measured  
Improvement: not measured  

Do not invent 55% / 88%.

## Hardware

Hardware tests not executed.

- LED: not executed
- USART: not executed
- PWM: not executed
- EXTI: not executed
- ADC: not executed

No Blue Pill / ST-Link / serial session was used in this run. Status would be `UNAVAILABLE` / Hardware Not Tested. Not PASS.

## Golden (real ARM GCC)

All eleven projects: `make` via `compile_project` produced `firmware.elf`, `firmware.hex`, `firmware.bin`.

| Golden | Compile |
|---|---|
| stm32f103_led | PASS |
| stm32f103_exti | PASS |
| stm32f103_tim_interrupt | PASS |
| stm32f103_pwm | PASS |
| stm32f103_usart | PASS |
| stm32f103_usart_it | PASS |
| stm32f103_usart_dma | PASS |
| stm32f103_adc | PASS |
| stm32f103_adc_dma | PASS |
| stm32f103_i2c | PASS |
| stm32f103_spi | PASS |

Based on official STM32CubeF1 HAL. No stub HAL.

## Known Failures

- Agent vs Baseline cannot run without a public LLM endpoint.
- Windows CI/dev hosts may skip symlink escape test.
- The upgraded CI definition installs and requires ARM GCC 13.3.1 for the Golden gate; its first remote run is NOT RUN in this checkout.
- `unigateway/` leftover directory is gitignored; not part of the Agent runtime.

## Known Limitations

- STM32F103 HAL is ready. The specifically registered ESP32-S3 ESP-IDF adapter is experimental; generic ESP32, STM32F407 and 8051 remain unsupported.
- Code-mode approval is in-process (lost on restart). `once`/`always` now distinguished (`always` persists for the run).
- Hardware loop max 3 flashes; PWM without a probe is PARTIAL.
- Official template Makefile already lists most HAL `.c` files; `register_hal_module` still exists for stripped Makefiles and Error Memory.
- Benchmark task definitions have expanded to 50; LLM evaluation remains SKIPPED until a fair same-model run is executed.

## Supported Features

- Next.js frontend + FastAPI backend, LIVE/DEMO/OFFLINE
- Agent runtime, planner, context (IOC > project.json > board > default)
- OpenAI-compatible LLM with SSRF host checks
- apply_patch, Code Mode approval (approve/reject/stop-while-waiting/once/always)
- Stop cancellation, SSE unique event ids
- Git snapshot / undo
- SQLite history, Error Memory with deterministic HAL module / IRQ fixes
- Official CubeF1 HAL/CMSIS, ARM GCC compile, GCC/LD parser, clangd, cppcheck
- Knowledge RAG / PDF ingest, MCU pin tools, IOC parser (DMA/NVIC/clock/GPIO fields)
- Peripheral skills + `configure_usart|adc|pwm|i2c|spi|exti` + `register_hal_module`
- Import existing STM32 tree scan/copy
- Hardware session persistence, 3-iteration flash loop, hardware status enum
- Validator package under `backend/app/validation/`
- Benchmark harness + schema, GitHub Actions

Suggested GitHub description:

`AI firmware engineering agent for STM32F103 — requirement → code → ARM GCC build → auto-fix → ST-Link flash → serial validation.`
