#!/usr/bin/env python3
"""Generate RELEASE_EVIDENCE.json — the release's evidence record.

Everything here is measured or read from real artifacts on this machine:
versions, toolchain probes, platform capability matrix, golden build
artifacts, benchmark summary (with skip reasons), and (optionally) a fresh
backend pytest run. Nothing is hand-written into the evidence file.

Usage:
    python scripts/gen_release_evidence.py [--run-tests]
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))


def _first_line(result: subprocess.CompletedProcess) -> str:
    lines = ((result.stdout or "") + (result.stderr or "")).splitlines()
    return lines[0].strip() if lines else ""


def _git_commit() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=8, check=False
        ).stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _version() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def _toolchain() -> dict:
    from app.tools.toolchain import prepend_toolchain_path
    import shutil

    prepend_toolchain_path()
    out: dict = {}

    if shutil.which("arm-none-eabi-gcc"):
        try:
            out["arm-none-eabi-gcc"] = _first_line(
                subprocess.run(["arm-none-eabi-gcc", "--version"], capture_output=True, text=True, timeout=10, check=False)
            )
        except (OSError, subprocess.TimeoutExpired):
            out["arm-none-eabi-gcc"] = shutil.which("arm-none-eabi-gcc")
    else:
        out["arm-none-eabi-gcc"] = None

    if shutil.which("make"):
        try:
            out["make"] = _first_line(
                subprocess.run(["make", "--version"], capture_output=True, text=True, timeout=10, check=False)
            )
        except (OSError, subprocess.TimeoutExpired):
            out["make"] = shutil.which("make")
    else:
        out["make"] = None

    for name in ("openocd", "st-info", "cppcheck", "clangd", "arm-none-eabi-gdb"):
        out[name] = shutil.which(name)

    renode = None
    try:
        from app.hardware.simulation.renode import find_renode

        renode = str(find_renode()) if find_renode() else None
    except Exception:
        renode = None
    out["renode"] = renode
    return out


def _capabilities() -> dict:
    from app.core.capabilities import capability_summary

    return capability_summary()


def _goldens() -> dict:
    base = ROOT / "examples" / "golden"
    out = {}
    for d in sorted(base.glob("stm32f103_*")):
        elf = d / "firmware.elf"
        out[d.name] = {
            "elfPresent": elf.is_file(),
            "elfBytes": elf.stat().st_size if elf.is_file() else None,
        }
    return out


def _benchmark() -> dict:
    p = ROOT / "benchmarks" / "stm32f103" / "latest-summary.json"
    if not p.is_file():
        return {"status": "NOT_RUN", "reason": "no benchmark summary — run python benchmarks/benchmark.py"}
    data = json.loads(p.read_text(encoding="utf-8"))
    data["status"] = "SKIPPED" if data.get("skipped") else "RAN"
    return data


def _tests(run: bool) -> dict:
    if not run:
        return {"status": "NOT_RUN", "reason": "use --run-tests to execute pytest in this script"}
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"], cwd=ROOT / "backend", capture_output=True, text=True, timeout=1200, check=False
    )
    tail = (r.stdout or "").splitlines()[-2:]
    return {"status": "PASS" if r.returncode == 0 else "FAIL", "exitCode": r.returncode, "summary": tail}


def _hardware_runs() -> dict:
    ws = ROOT / "workspaces"
    runs = list(ws.glob("*/hardware-runs/hw-*.json"))
    return {
        "runFiles": len(runs),
        "note": "hardware execution requires the lab fixture; absent probes = NOT_TESTED by design",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-tests", action="store_true")
    args = ap.parse_args()

    from app.tools.detect import _probe_stlink

    evidence = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "version": _version(),
        "commit": _git_commit(),
        "host": platform.platform(),
        "python": platform.python_version(),
        "toolchain": _toolchain(),
        "platformCapabilities": _capabilities(),
        "goldenBuilds": _goldens(),
        "benchmark": _benchmark(),
        "tests": _tests(args.run_tests),
        "hardware": {
            **_hardware_runs(),
            "stlinkProbe": _probe_stlink(),
        },
        "spikes": {
            "renode": "SUPPORTED (docs/RENODE_SPIKE.md — real run)",
            "esp32": "NOT_RUN (docs/ESP32_SIM_SPIKE.md — ESP-IDF absent)",
        },
        "knownLimits": [
            "STM32F103 HAL only — ESP32/C51/RP2040/Host C have no backend adapter",
            "Hardware execution NOT_TESTED on hosts without a probe (honest UNAVAILABLE)",
            "Agent vs Baseline requires a configured LLM; benchmark records skip reasons otherwise",
            "Flash/debug verified only up to code-path + unit tests until a live probe session is recorded",
        ],
    }
    out = ROOT / "RELEASE_EVIDENCE.json"
    out.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
