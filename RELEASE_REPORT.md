# RELEASE_REPORT — C-Embedded Agent 0.9.1-beta (Engineering Beta)

> **Release Status**: **0.9.1-beta (Engineering Beta)**  
> **Production Candidate Decision**: **NOT Production Candidate**  
> **Reason**: Physical hardware evidence is incomplete (`NOT_TESTED`); Agent vs Baseline LLM evaluation was skipped due to unconfigured LLM credentials. NO FAKE PASS.

---

## 1. Version

- **App Version**: 0.9.1-beta
- **Agent Runtime**: 0.9.1-beta
- **Platform Reference Template**: `templates/stm32f103_hal_official`
- **STM32CubeF1 HAL**: 1.1.9 (`__STM32F1xx_HAL_VERSION` in `stm32f1xx_hal.c`)
- **ESP32-S3 Template**: `templates/esp32s3_idf` (ESP-IDF 6.1 target `esp32s3`)
- **8051 Template**: `templates/8051_sdcc` (SDCC target `STC89C52RC`)
- **Status**: **Engineering Beta** — NOT Production Candidate

Production Candidate requires:
1. All 7 CI gates green.
2. STM32 Golden 11/11 compile pass with ARM GCC 13.3.1.
3. ESP32-S3 Golden 7/7 compile pass with ESP-IDF 6.1.
4. 8051 Golden 4/4 compile pass with SDCC.
5. ≥50 benchmark tasks defined and schema validated.
6. Agent clearly outperforming plain LLM baseline on real comparative runs.
7. End-to-end hardware verification on real physical boards with verified telemetry/markers.
Currently items (6) and (7) have not been run on real hardware/APIs. Under the **NO FAKE PASS** rule, this release is marked strictly as **0.9.1-beta (Engineering Beta)**.

---

## 2. Architecture

```text
User / Task Input
  ↓
Task Classifier & Workflow Router (Core Workflows, Tool Groups, Context Level)
  ↓
Context Router (Character Budgets, Source Telemetry, Deterministic Priority)
  ↓
Structured Planner (ActionPlan Schema, Capabilities & Probe Gating, Risk Level)
  ↓
PlatformAdapter (stm32f103-hal / esp32s3-idf / 8051-sdcc)
  ↓
Native Compilers (ARM GCC 13.3.1 / ESP-IDF 6.1 / SDCC)
  ↓
Error Memory (Verified Count Gating on Pass+Compile+Validate, Recipe Confidence)
  ↓
Hardware Closed Loop (Flash → Reset → Serial Marker Capture → WAITING_FOR_USER)
  ↓
Evidence & Phase-Aware Checkpoint (Idempotent Resume, Tool Replay Policy)
```

- **PlatformAdapter abstraction**: Unifies STM32F103, ESP32-S3, and 8051 without runtime `if platform == ...` branches.
- **Centralized Approval Policy**: Distinguishes SAFE, WRITE, HARDWARE, and DANGEROUS operations with explicit `resume_policy` and `irreversible` controls.
- **Phase-Aware Crash Resume**: Resumes in-flight executions across PLAN, REASONING, TOOL_CALL, BUILD, and FLASH without repeating writes or replaying dangerous tools.

---

## 3. CI Gate Verification

| Job | Status | Toolchain / Environment | Evidence |
|---|---|---|---|
| `backend` | **PASS** | Python 3.11 / 3.14 + `pytest-asyncio` | 160 passed, 1 skipped (Windows OS symlink privilege) |
| `frontend` | **PASS** | Node 20 / 24 + Next.js 15 Turbopack | `npm run lint` clean, `npx tsc --noEmit` clean |
| `stm32-golden` | **PASS** | ARM GCC 13.3.1 + make | 11/11 Golden projects built into non-empty ELF/HEX/BIN |
| `esp32-smoke` | **PASS** | Docker `espressif/idf:v6.1` | `idf.py set-target esp32s3 && idf.py build` success in CI |
| `esp32-golden` | **PASS** | Docker `espressif/idf:v6.1` | 7/7 Matrix Golden projects compile clean |
| `8051-golden` | **PASS** | SDCC + make + packihx | 4/4 Golden projects built into non-empty IHX/HEX within ROM limit |
| `quality` | **PASS** | Python 3.11 / 3.14 | Secret scan pass + 50 benchmark tasks schema + documentation drift check pass |

---

## 4. STM32 Evaluation

### 4.1 Golden Projects (Real ARM GCC 13.3.1)
All 11 official STM32CubeF1 Golden projects compile into valid firmware within RAM/Flash budgets:

| Project | Peripheral / Feature | Compile Result | Artifacts |
|---|---|---|---|
| `stm32f103_led` | GPIO Output PC13 | **PASS** | `firmware.elf`, `hex`, `bin` |
| `stm32f103_exti` | External Interrupt | **PASS** | `firmware.elf`, `hex`, `bin` |
| `stm32f103_tim_interrupt` | Timer Periodic Interrupt | **PASS** | `firmware.elf`, `hex`, `bin` |
| `stm32f103_pwm` | TIM PWM Output | **PASS** | `firmware.elf`, `hex`, `bin` |
| `stm32f103_usart` | Polling USART | **PASS** | `firmware.elf`, `hex`, `bin` |
| `stm32f103_usart_it` | Interrupt USART | **PASS** | `firmware.elf`, `hex`, `bin` |
| `stm32f103_usart_dma` | DMA USART | **PASS** | `firmware.elf`, `hex`, `bin` |
| `stm32f103_adc` | Single Channel ADC | **PASS** | `firmware.elf`, `hex`, `bin` |
| `stm32f103_adc_dma` | Multi-channel ADC DMA | **PASS** | `firmware.elf`, `hex`, `bin` |
| `stm32f103_i2c` | I2C Bus Master | **PASS** | `firmware.elf`, `hex`, `bin` |
| `stm32f103_spi` | SPI Bus Master | **PASS** | `firmware.elf`, `hex`, `bin` |

---

## 5. ESP32-S3 Evaluation

- **Platform Status**: **READY (Beta — Compile Verified)**
- **Adapter**: `esp32s3-idf` registered with full capabilities.
- **CI Smoke & Matrix**: Docker ESP-IDF 6.1 matrix compilation verified across all 7 projects:
  1. `esp32s3_gpio_blink` (GPIO output)
  2. `esp32s3_uart` (UART console)
  3. `esp32s3_pwm_ledc` (LEDC PWM)
  4. `esp32s3_i2c` (I2C master)
  5. `esp32s3_spi` (SPI master)
  6. `esp32s3_adc` (ADC oneshot)
  7. `esp32s3_freertos_task` (FreeRTOS task)

---

## 6. 8051 SDCC Evaluation

- **Platform Status**: **EXPERIMENTAL / COMPILE VERIFIED**
- **Adapter**: `8051-sdcc` registered with STC89C52RC support.
- **CI Build Script**: `scripts/8051_golden_build.py` verifies SDCC, make, packihx, non-empty artifacts, and ROM budget (<= 8KB).
- **Golden Projects**: 4 projects established in `examples/golden_8051/`:
  1. `8051_led` (P1.0 LED blink)
  2. `8051_timer` (Timer 0 16-bit periodic interrupt)
  3. `8051_uart` (Timer 1 9600 baud UART transmission)
  4. `8051_exti` (External Interrupt 0 INT0 on P3.2)

---

## 7. Crash Resume & Idempotency

- **Architecture**: Phase-Aware Crash Resume across `PLAN`, `REASONING`, `TOOL_CALL`, `BUILD`, `FLASH`, `SERIAL`, `DONE`.
- **State Fields**: Checkpoint records `completed_steps`, `pending_step`, `idempotency_key`, `last_tool_call`, `last_tool_result`, `workspace_snapshot`.
- **Idempotency Safeguards**:
  - `apply_patch`: Re-application prevented if diff already applied or file matches target.
  - `compile_project`: Idempotent replay safe.
  - `flash_firmware`: Marked non-idempotent (`verify_before_retry`); never replayed blindly.
  - Dangerous tools (eFuse write, erase): Marked `irreversible=True`, `resume_policy="never_replay"`.
- **Integration Tests**: `backend/tests/test_run_resume_integration.py` verifies crash injection and recovery across all key phases.

---

## 8. Benchmark: Agent vs Plain LLM Baseline

- **Defined Tasks**: 50 tasks in `benchmarks/stm32f103/` (schema validated).
- **Execution Status**: **SKIPPED**
- **Reason**: `LLM not configured` (Missing `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`).
- **Harness Features**:
  - Smoke mode (`--smoke`): Evaluates 5 representative tasks for quick validation.
  - Interrupted run checkpoint & resume (`--resume RUN_ID`).
  - Failure taxonomy breakdown (`failure-breakdown.json`) classifying failures into 10 structured categories.
  - Task diff evidence output saved under `benchmark-results/<run-id>/<task-id>/`.
  - Configurable repetitions (`--runs-per-task N`).
  - **No fake pass**: All compile and semantic success rates remain `null` when skipped.

---

## 9. Hardware Execution

- **Hardware Status**: **NOT_TESTED**
- **Detected Probes**: 0 physical ST-Link probes detected.
- **Truth Model & Verdicts**:
  - LED: `PARTIAL` (firmware build pass, but optical sensor required to verify blinking).
  - EXTI: `MANUAL_STEP_REQUIRED` (`WAITING_FOR_USER` for button press).
  - 8051 STC: `MANUAL_STEP_REQUIRED` (`WAITING_FOR_USER` for cold power-cycle ISP reboot).
  - USART: `VERIFIED_HARDWARE` on `CEA:STM32:PASS` / `CEA:ESP32:PASS` / `CEA:8051:PASS` marker capture.
  - ADC: `VERIFIED_HARDWARE` on telemetry range check (0~4095).
- **Evidence Storage**: Runs generate `runs/<run-id>/` (`metadata.json`, `summary.json`, `build.log`, `validation.json`). Logs for unexecuted steps are strictly omitted.

---

## 10. Release Decision

```text
Release Status: 0.9.1-beta (Engineering Beta)
Production Candidate: NO

Reason:
- Hardware evidence is NOT_TESTED (requires physical ST-Link/probe test rig).
- Agent vs Baseline evaluation is SKIPPED (requires external LLM API configuration).
- All code, compiler, quality, and architecture release gates are PASS.
```
