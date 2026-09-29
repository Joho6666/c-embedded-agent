# ESP32_SIM_SPIKE — ESP32 emulation feasibility (v0.10 Phase G)

**Verdict: NOT_RUN — ESP32 toolchain absent on this machine (environment evidence below).**
No support is claimed and none is inferred. This document records what was checked,
what would be required, and the decision rule for upgrading the verdict.

## Environment evidence (2026-09-06, this machine)

| Check | Result |
|---|---|
| `idf.py` on PATH | not found |
| `IDF_PATH` env | empty |
| `esptool` (host python + repo venv) | not installed |
| ESP-IDF install under `%USERPROFILE%` / Program Files | none found |

## What the spike requires (prepared, not executed)

1. ESP-IDF ≥ 5.x with `esp-idf` master for ESP32-S3.
2. A minimal UART-emitting app (`hello_world`-class) built with `idf.py build`.
3. An emulation path, evaluated against **real runs only**:
   - `pytest-embedded` + Renode's ESP32 support (Renode models ESP32-C3/S3
     partially — must be proven per-variant), or
   - QEMU (`esp-develop` fork) with `esp32s3` machine, or
   - `esp-emu` if it covers the target variant.
4. Evidence chain identical to the STM32 path: ELF → emulator → UART line
   → `CEA:SIM:PASS` token → `level=SIMULATION` EvidenceRecord.

## Decision rule

- Emulator boots an IDF-built S3 app and real UART lines are captured →
  verdict becomes **PARTIAL** (build+UART proven; Wi-Fi/BLE not emulated).
- Full chain automated behind `SimulationAdapter` for one board → **SUPPORTED**
  for that board's UART tasks only.
- Wi-Fi/BLE cannot be claimed from emulation without real RF hardware — those
  stay HARDWARE-only tasks.

## Where it plugs in

`app/hardware/simulation/` is target-agnostic: an `EspidfAdapter` would
implement the same `SimulationAdapter` interface (detect / run / stop) and
join `list_adapters()`. The capability matrix (Phase I) will show
`SIMULATE: NOT_SUPPORTED` for esp32s3-idf until a real run changes it.
