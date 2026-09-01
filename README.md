# C-Embedded Agent

AI firmware engineering agent for STM32F103 — requirement → code → ARM GCC build → auto-fix → ST-Link flash → serial validation.

Version: **0.8.0-beta** (Late Beta). Not a Production Candidate: Agent vs Baseline was not executed (no LLM configured on this machine).

The evaluation question is not “how many pages were added?”. It is:

- On the same STM32F103 task, how often does a plain LLM compile?
- How often does C-Embedded Agent compile and pass semantic validation?

## Support Matrix

| Platform | Build | Agent | Flash | Hardware Validate |
|---|---|---|---|---|
| STM32F103 HAL | ✅ | Beta | Beta | Beta |
| STM32F407 | ❌ | ❌ | ❌ | ❌ |
| ESP32 | ❌ | ❌ | ❌ | ❌ |
| 8051 | ❌ | ❌ | ❌ | ❌ |

Do not claim ESP32 / 8051 / F407 are available.

## Modes

- **DEMO**: backend not running. Top bar DEMO. Frontend mock only — never pretends LIVE success.
- **LIVE**: FastAPI running. Missing `arm-none-eabi-gcc` is reported as missing; **never** fakes Build Successful.
- **OFFLINE**: API URL configured but backend unreachable.

## Start

```bash
npm install
npm run dev
```

```bash
pip install -r backend/requirements.txt
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open http://localhost:3000

See `.env.example`. LLM must be public http/https (localhost / private hosts rejected). Without LLM the Agent reports unavailable and still tries `make`.

`GET /api/version` returns App / Agent Runtime / Template / STM32CubeF1 versions. HAL/CMSIS pin is `vendor.lock.json`.

## STM32F103 official template

Default project: `templates/stm32f103_hal_official` (STM32CubeF1 CMSIS + HAL, not a stub).

- MCU: STM32F103C8T6
- Board: Blue Pill
- LED: **PC13**, 500ms toggle
- Sync official drivers: `python scripts/sync_cubef1.py`

```bash
cd templates/stm32f103_hal_official
make clean && make -j4
```

Needs `arm-none-eabi-gcc` / `objcopy` / `size` / `make`. Tests skip when the toolchain is absent — they do not invent scores.

Portable toolchain autodetection:

- `%USERPROFILE%/tools/xpack-arm-none-eabi-gcc-13.3.1-1.1/bin`
- `%USERPROFILE%/tools/xpack-windows-build-tools-4.4.1-3/bin`

or `CEA_TOOLCHAIN_PATH`.

## Golden projects

All of the following compiled on this machine with ARM GCC 13.3 into `firmware.elf` / `.hex` / `.bin`:

| Project | Path |
|---|---|
| LED | `examples/golden/stm32f103_led/` |
| EXTI | `examples/golden/stm32f103_exti/` |
| TIM interrupt | `examples/golden/stm32f103_tim_interrupt/` |
| PWM | `examples/golden/stm32f103_pwm/` |
| USART | `examples/golden/stm32f103_usart/` |
| USART interrupt | `examples/golden/stm32f103_usart_it/` |
| USART DMA | `examples/golden/stm32f103_usart_dma/` |
| ADC poll | `examples/golden/stm32f103_adc/` |
| ADC DMA | `examples/golden/stm32f103_adc_dma/` |
| I2C | `examples/golden/stm32f103_i2c/` |
| SPI | `examples/golden/stm32f103_spi/` |

Refresh: `python examples/golden/sync_overlay.py all`

## Agent rules

Read the tree → Knowledge / MCU pin / IOC / Skill recipe → `configure_*` for init → LLM writes application logic → `make` → known Error Memory fix before asking the model again.

Default writes are limited to `Core/Src` and `Core/Inc`. Protected: `Drivers/`, `Middlewares/`, `startup*.s`, `*.ld`, `Makefile`, `*.ioc`. HAL sources are registered with `register_hal_module`, not by letting the model edit the Makefile.

Context priority: **IOC > project.json > Board Profile > Default**.

Existing STM32 trees can be scanned/imported (`scan_existing_project` / `POST /api/projects/import-existing`) instead of rebuilding from the template. Import-ioc still creates a template project plus the `.ioc` sidecar.

## Hardware

Build → compile fix → Flash → verify reset → Serial → hardware validator. At most **3** flash iterations. Status is one of `PASS | FAIL | PARTIAL | UNKNOWN | UNAVAILABLE`. PWM without a probe is `PARTIAL`. LED without GPIO feedback is static pass + hardware `UNVERIFIED`. No board → **Hardware Not Tested**, never PASS.

Per-project session: `hardware-session.json` (`debugger`, `serialDevice`, `baud`, `board`, `mcu`).

USART expect: `CEA:USART:PASS`. ADC expect: `CEA:ADC:value=` in 0–4095.

## Benchmark

```bash
python benchmarks/benchmark.py
```

Writes:

- `benchmarks/stm32f103/results.json`
- `benchmarks/stm32f103/latest-summary.json` (commit this)
- `benchmarks/comparison-summary.json` (Agent vs Baseline)

This checkout: ARM GCC present, **LLM not configured**. Summary records skip reasons and zeros. Template itself compiled (`template_build: true`). No fake Agent vs Baseline percentages.

## Tests / CI

```bash
cd backend && python -m pytest -q
npm run build
```

GitHub Actions: frontend `npm ci && npm run build`, backend `pytest`. ARM GCC is optional (golden `make` tests skip).

Leftover Universal AI Gateway tests (`tests/test_gateway.py`, `tests/test_v090.py`) are **ignored** by pytest. They target `/v1` / `/admin` which this app does not mount. That is not deleting Agent tests.

`unigateway/` is an independent mock console from an older graft. It is not imported by the Embedded Agent. Do not treat it as part of this product.

This release is STM32F103 only.
