# Behavioural simulation (Renode)

Compiling proves firmware links. Simulation proves what it **does**. `backend/app/sim/renode.py`
runs a built STM32F103 ELF on a simulated Blue Pill in [Renode](https://github.com/renode/renode)
and asserts behaviour with Renode's own Robot Framework keywords:

- LED blink timing — `Assert LED Is Blinking` (on/off durations, ±5 % by default)
- UART output — `Wait For Line On Uart`

Evidence is reported as `SIMULATED`, distinct from real hardware. Missing Renode or Robot
dependencies yield `UNAVAILABLE`, never `PASS`.

## Why a custom board model

Renode's stock `stm32f103.repl` cannot run a real STM32CubeF1 clock init:

| Problem | Symptom | Fix (added in the generated board) |
|---|---|---|
| `RCC_CR` is a constant tag with `PLLRDY` always set | `HAL_RCC_OscConfig` spins forever waiting for the PLL to stop | `renode_models/stm32f1_rcc.py`: ready bits follow enable bits, `CFGR.SWS` mirrors `SW` |
| `FLASH_ACR` not modelled | `HAL_RCC_ClockConfig` latency read-back fails | `renode_models/register_file.py` |
| Peripheral bit-band alias (`0x42000000`) unmapped | HAL `__HAL_RCC_PLL_ENABLE()` writes are dropped | `Miscellaneous.BitBanding` with `peripheralBase: 0x40000000` |
| Blue Pill LED is active-low | polarity errors invisible | LED on PC13 with `invert: true` |

Known limits: clock gating and GPIO/UART clock enables are not enforced by the model, and UART
baud rate is not checked. Treat `SIMULATED` as strong behavioural evidence, not a replacement
for a hardware run.

## Usage

```bash
cd backend
python -m app.sim.renode --elf ../examples/golden/stm32f103_usart/firmware.elf --led C13:0.5 --uart usart1:Hello
```

Renode is found via `CEA_RENODE_PATH`, `renode` on `PATH`, or `~/tools/renode*/`. Robot
dependencies (`robotframework==6.1`, `psutil`, `pyyaml`) are found via `CEA_RENODE_PYTHON`,
`~/tools/renode-venv`, or the current interpreter.

## In the agent

The `simulate_firmware` tool takes `{"led": [{"pin": "PC13", "on_ms": 500, "off_ms": 500}],
"uart": [{"peripheral": "usart1", "expect": "Hello"}]}`. When a task has observable behaviour
the loop stays open after a successful build so the model can simulate, fix and re-verify; a
failed simulation fails the run, an unavailable simulator does not.

## Behaviour-graded arena

`benchmarks/sim_arena.py` grades every arm (reference, template, plain LLM, this agent, and
local coding CLIs) with the same clean build → static validation → simulation pipeline on
`benchmarks/stm32f103_sim/`. Controls: reference solutions pass 5/5, the untouched template
passes 0/5 — while static validation alone accepts it on 2/5.
