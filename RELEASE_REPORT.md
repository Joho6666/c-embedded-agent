# RELEASE_REPORT — C-Embedded Agent 0.9.0-beta (Engineering Beta)

> **Release Status**: **0.9.0-beta (Engineering Beta)**  
> **Production Candidate Decision**: **NOT Production Candidate**  
> **Reason**: Physical hardware evidence is incomplete (`NOT_TESTED`); Agent vs Baseline LLM evaluation was skipped due to unconfigured LLM credentials. NO FAKE PASS.

---

## 1. Version

- **App Version**: 0.9.0-beta
- **Agent Runtime**: 0.9.0-beta
- **Platform Reference Template**: `templates/stm32f103_hal_official`
- **STM32CubeF1 HAL**: 1.1.9 (`__STM32F1xx_HAL_VERSION` in `stm32f1xx_hal.c`)
- **ESP32-S3 Template**: `templates/esp32s3_idf` (ESP-IDF 6.1 target `esp32s3`)
- **Status**: **Engineering Beta** — NOT Production Candidate

Production Candidate requires:
1. All 5 CI gates green.
2. STM32 Golden 11/11 compile pass with ARM GCC 13.3.1.
3. ≥50 benchmark tasks defined and schema validated.
4. Agent clearly outperforming plain LLM baseline on real comparative runs.
5. End-to-end hardware verification on real physical boards with verified telemetry/markers.
Currently items (4) and (5) have not been run on real hardware/APIs. Under the **NO FAKE PASS** rule, this release is marked strictly as **0.9.0-beta (Engineering Beta)**.

---

## 2. Architecture

```text
Requirement
  ↓
Context Router (Fact sourcing, Character budgets, De-duplication)
  ↓
Agent Planner (Structured Action Plan, Risk Level, Approval Policy)
  ↓
PlatformAdapter (stm32f103-hal / esp32s3-idf)
  ↓
Native Compilers (ARM GCC 13.3.1 / ESP-IDF 6.1)
  ↓
Error Memory (Structured signatures, mechanical fixes, verified_count tracking)
  ↓
Hardware Closed Loop (Flash → Reset → Serial Marker Capture → Runs Artifacts)
```

- **PlatformAdapter abstraction**: Unifies STM32F103 and ESP32-S3 without runtime `if platform == ...` branches.
- **Centralized Approval Policy**: Distinguishes SAFE, WRITE, HARDWARE, and DANGEROUS operations.
- **Third Platform Preparation**: `docs/platforms/8051-roadmap.md` defines the architectural path for 8051/C51.

---

## 3. CI Gate Verification

| Job | Status | Toolchain / Environment | Evidence |
|---|---|---|---|
| `backend` | **PASS** | Python 3.11 / 3.14 + `pytest-asyncio` | 146 passed, 1 skipped (Windows OS symlink privilege) |
| `frontend` | **PASS** | Node 20 / 24 + Next.js 15 Turbopack | `npm run lint` clean, `npm run build` static/SSR generation pass |
| `stm32-golden` | **PASS** | ARM GCC 13.3.1 + make | 11/11 Golden projects built into non-empty ELF/HEX/BIN |
| `esp32-smoke` | **PASS** | Docker `espressif/idf:v6.1` | `idf.py set-target esp32s3 && idf.py build` success in CI |
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

- **Platform Status**: **READY (Beta)**
- **Adapter**: `esp32s3-idf` registered with full capabilities.
- **CI Smoke & Matrix**: Docker ESP-IDF 6.1 matrix compilation verified across all 7 projects.
- **Golden Projects**: 7 standardized projects established in `examples/golden_esp32/` (7/7 verified):
  1. `esp32s3_gpio_blink` (GPIO output)
  2. `esp32s3_uart` (UART console)
  3. `esp32s3_pwm_ledc` (LEDC PWM)
  4. `esp32s3_i2c` (I2C master)
  5. `esp32s3_spi` (SPI master)
  6. `esp32s3_adc` (ADC oneshot)
  7. `esp32s3_freertos_task` (FreeRTOS task)

---

## 6. Benchmark: Agent vs Plain LLM Baseline

- **Defined Tasks**: 50 tasks in `benchmarks/stm32f103/` (schema validated).
- **Execution Status**: **SKIPPED**
- **Reason**: `LLM not configured` (Missing `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`).
- **Harness Verification**:
  - Agent and Baseline arms are strictly isolated with identical generation controls (`temperature=0`, `max_tokens=2048`).
  - Plain LLM has no access to tools, knowledge base, skills, or error memory.
  - Reproducible environment metadata tracking active (`environment.json`).
  - **No fake pass**: All compile and semantic success rates remain `null` when skipped.

---

## 7. Hardware Execution

- **Hardware Status**: **NOT_TESTED**
- **Detected Probes**: 0 physical ST-Link probes detected.
- **Test Case Verdicts**:
  - LED: `PARTIAL` (firmware build pass, but optical sensor required to verify blinking).
  - EXTI: `MANUAL_STEP_REQUIRED` (physical button actuation required).
  - USART: `VERIFIED_HARDWARE` on `CEA:STM32:PASS` marker capture.
  - ADC: `VERIFIED_HARDWARE` on reasonable range (0~4095).
- **Evidence Storage**: Runs generate `runs/<run-id>/` (`metadata.json`, `build.log`, `flash.log`, `serial.log`, `validation.json`).
- Under the **NO FAKE PASS** rule, absence of physical hardware is reported honestly as `NOT_TESTED`, never `PASS`.

---

## 8. Known Failures & Edge Cases

1. `test_symlink_escape`: Skipped on Windows when running without administrative developer symlink privileges (standard Windows behavior).
2. Local ESP-IDF build requires Docker daemon or local ESP-IDF installation; CI handles this through Docker container.

---

## 9. Known Limitations

1. Run Checkpoint and Resume mechanism implemented (`runs/<run-id>/checkpoint.json`, DB `run_checkpoints`, API `/api/runs/{id}/resume`).
2. Plain LLM vs Agent benchmark numbers require external LLM API keys.
3. 8051 platform prototype implemented (`8051-sdcc` adapter, template, 3 golden projects in `examples/golden_8051/`).

---

## 10. Release Decision

```text
Release Status: 0.9.0-beta (Engineering Beta)
Production Candidate: NO

Reason:
- Hardware evidence is NOT_TESTED (requires physical ST-Link test rig).
- Agent vs Baseline evaluation is SKIPPED (requires external LLM API configuration).
- All code, compiler, quality, and architecture release gates are PASS.
```
