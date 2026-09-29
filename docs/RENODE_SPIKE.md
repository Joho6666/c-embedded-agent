# RENODE_SPIKE — Level-2 simulation feasibility (v0.10 Phase F)

**Verdict: SUPPORTED for STM32F103** — real run documented below.

This spike answers the brief's question: can the C-Embedded Agent produce
genuine *Simulation evidence* (ELF → emulator → UART → expect-token →
evidence) without physical hardware? Answer, from an actual run on this
machine: yes.

## What was actually executed (2026-09-06)

1. **Emulator**: Renode 1.15.3 portable (vendored to `~/tools/renode-portable/renode_1.15.3/`,
   24.9 MB zip from the official GitHub release).
2. **Firmware**: `backend/tests/fixtures/renode_spike/sim_uart.c` — minimal
   STM32F103C8 firmware (the Blue Pill MCU), no HAL, registers direct:
   USART1 CR1 `UE|TE`, poll `TXE`, emit `CEA:SIM:PASS\r\n`, toggle PC13.
   Built with the repo's own ARM GCC 13.3.1: 135 bytes text.
3. **Platform**: Renode's stock `platforms/cpus/stm32f103.repl` (usart1–5,
   gpioPortA–E, NVIC, RCC). The Blue Pill *board* is not a Renode platform,
   but the MCU-level platform is exactly the target family.
4. **Run** (headless): `Renode.exe --console --disable-xwt -e "include @spike.resc"`
   with `sysbus.usart1 CreateFileBackend @uart.log` + `sysbus LoadELF` + `start`.
5. **Result**: `uart.log` filled with `CEA:SIM:PASS` lines within seconds;
   expect-match → SIMULATION evidence.

## Findings (all empirical)

- **Renode's STM32_UART drops characters unless CR1 `UE|TE` are set** — the
  first run produced only `WARNING usart1: transmitter is not enabled`. This
  is a *feature* for the evidence model: sloppy init is visible in
  simulation exactly like on hardware.
- Headless UART capture works via `CreateFileBackend`; no GUI needed.
- The spike needs no Renode Robot Framework — the monitor CLI is enough,
  which keeps CI simple (`--console` + stdin `q`).
- Simulation evidence is recorded with `level=SIMULATION` via
  `app/hardware/evidence.py` and reported as its own level: **Build PASS ≠
  Simulation PASS ≠ Hardware PASS** stays true.

## Adapter

`app/hardware/simulation/renode.py::RenodeAdapter` implements the
`SimulationAdapter` interface (detect / run / stop). Discovery order:
`CEA_RENODE_PATH` → PATH → vendored `~/tools/renode-portable/renode_*/bin/Renode.exe`.
`detect()` reports NOT_INSTALLED honestly when absent; `run()` returns
UNAVAILABLE with reason "simulation NOT_RUN (never faked)".

Test: `backend/tests/test_simulation.py::test_renode_real_spike_stm32f103`
(skips honestly when Renode or the ELF is absent; runs for real otherwise).

## Limits — do not overclaim

- This validates **one MCU family** (STM32F103) with register-level
  firmware. HAL-heavy projects also run (Renode models the F1 peripherals
  used by the HAL), but each peripheral model needs a real test before
  claiming it.
- GPIO/ADC/I2C/SPI peripheral *behavior* (as opposed to UART) is not yet
  exercised by the spike; PWM/I2C/SPI simulation validators are future work.
- Simulation PASS never upgrades to Hardware PASS — the three-level report
  keeps them separate by construction.

## Reproduce

```bash
arm-none-eabi-gcc -mcpu=cortex-m3 -mthumb -T f103.ld -nostdlib -O1 sim_uart.c -o sim_uart.elf
cd ~/tools/renode-portable/renode_1.15.3
./bin/Renode.exe --console --disable-xwt -e "include @<repo>/backend/tests/fixtures/renode_spike/spike.resc"
# → backend/tests/fixtures/renode_spike/uart.log contains CEA:SIM:PASS
python -m pytest backend/tests/test_simulation.py -q
```
