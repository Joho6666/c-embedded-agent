"""Run STM32F103 firmware in Renode and assert its behaviour.

Compiling proves the code links; this proves what it *does*: an LED toggles with
the requested period, a UART prints the requested text. Each check becomes one
Robot Framework test case on a fresh simulated Blue Pill, executed through
Renode's own test runner, and the verdict is parsed from Robot's XML output.

Evidence rules match the hardware path: when Renode or its Python test
dependencies are missing the result is ``UNAVAILABLE`` — never ``PASS``.
Simulation evidence is reported as ``SIMULATED``, distinct from real hardware.

CLI::

    python -m app.sim.renode --elf firmware.elf --led C13:0.5 --uart usart1:Hello
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

MODELS_DIR = Path(__file__).resolve().parent / "renode_models"
DEFAULT_TIMEOUT_SEC = 240


@dataclass(frozen=True)
class LedBlinkCheck:
    """GPIO pin drives an LED that must blink with the given on/off durations (seconds)."""

    port: str = "C"
    pin: int = 13
    on: float = 0.5
    off: float = 0.5
    tolerance: float = 0.05
    duration: float = 4.0
    active_low: bool = True

    @property
    def name(self) -> str:
        return f"LED P{self.port}{self.pin} blinks {self.on}s on / {self.off}s off"


@dataclass(frozen=True)
class UartExpectCheck:
    """A UART must print a line containing ``expect`` within ``timeout`` virtual seconds."""

    peripheral: str = "usart1"
    expect: str = "Hello"
    timeout: float = 3.0

    @property
    def name(self) -> str:
        return f"{self.peripheral} prints {self.expect!r}"


Check = LedBlinkCheck | UartExpectCheck


@dataclass
class SimResult:
    status: str  # PASS | FAIL | UNAVAILABLE
    checks: list[dict[str, Any]] = field(default_factory=list)
    reason: str | None = None
    evidence: dict[str, str] = field(default_factory=dict)
    kind: str = "SIMULATED"
    simulator: str = "renode"

    @property
    def success(self) -> bool:
        return self.status == "PASS"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"success": self.success}


def find_renode() -> Path | None:
    """Renode install root (the directory containing ``bin/`` and ``tests/``)."""
    candidates: list[Path] = []
    if os.environ.get("CEA_RENODE_PATH"):
        candidates.append(Path(os.environ["CEA_RENODE_PATH"]))
    exe = shutil.which("renode") or shutil.which("Renode")
    if exe:
        candidates.append(Path(exe).resolve().parent.parent)
    tools = Path.home() / "tools"
    for pattern in ("renode*/renode_*", "renode*"):
        candidates.extend(sorted(tools.glob(pattern), reverse=True))
    for root in candidates:
        if (root / "tests" / "run_tests.py").is_file() and (root / "platforms" / "cpus" / "stm32f103.repl").is_file():
            return root
    return None


def find_test_python() -> str | None:
    """A Python interpreter that can import Robot Framework for Renode's runner."""
    candidates = [os.environ.get("CEA_RENODE_PYTHON", "")]
    venv = Path.home() / "tools" / "renode-venv"
    candidates += [str(venv / "Scripts" / "python.exe"), str(venv / "bin" / "python"), sys.executable]
    for exe in candidates:
        if not exe or not Path(exe).is_file():
            continue
        probe = subprocess.run([exe, "-c", "import robot, psutil, yaml"], capture_output=True, stdin=subprocess.DEVNULL, check=False)
        if probe.returncode == 0:
            return exe
    return None


def _posix(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def _board_description(leds: list[LedBlinkCheck]) -> list[str]:
    lines = [
        # RCC with ready handshakes + FLASH_ACR read-back: needed by CubeF1 SystemClock_Config.
        "rcc: Python.PythonPeripheral @ sysbus 0x40021000",
        "    size: 0x400",
        "    initable: true",
        f'    filename: "{_posix(MODELS_DIR / "stm32f1_rcc.py")}"',
        "",
        "flashCtrl: Python.PythonPeripheral @ sysbus 0x40022000",
        "    size: 0x400",
        "    initable: true",
        f'    filename: "{_posix(MODELS_DIR / "register_file.py")}"',
        "",
        # HAL toggles RCC bits through the Cortex-M3 peripheral bit-band alias.
        "bitbandPeripherals: Miscellaneous.BitBanding @ sysbus <0x42000000, +0x2000000>",
        "    peripheralBase: 0x40000000",
    ]
    for led in leds:
        name = f"led{led.port.lower()}{led.pin}"
        port = f"gpioPort{led.port.upper()}"
        lines += [
            "",
            f"{name}: Miscellaneous.LED @ {port} {led.pin}",
            f"    invert: {'true' if led.active_low else 'false'}",
            "",
            f"{port}:",
            f"    {led.pin} -> {name}@0",
        ]
    return lines


def _robot_literal(text: str) -> str:
    """Escape free text for a single Robot Framework cell."""
    text = text.replace("\\", "\\\\").replace("${", "\\${").replace("@{", "\\@{").replace("%{", "\\%{")
    return text.replace("  ", " ${SPACE}").replace("\t", "${SPACE}")


def build_robot_suite(elf: Path, checks: list[Check]) -> str:
    leds = [c for c in checks if isinstance(c, LedBlinkCheck)]
    board = _board_description(leds)
    out = [
        "*** Settings ***",
        "Suite Setup       Setup",
        "Suite Teardown    Teardown",
        "Test Teardown     Test Teardown",
        "Resource          ${RENODEKEYWORDS}",
        "",
        "*** Keywords ***",
        "Create Board",
        "    ${board}=    Catenate    SEPARATOR=\\n",
    ]
    for line in board:
        stripped = line.lstrip(" ")
        indent = len(line) - len(stripped)
        cell = ("${SPACE*%d}" % indent if indent else "") + stripped if stripped else "${EMPTY}"
        out.append(f"    ...    {cell}")
    out += [
        '    Execute Command    mach create "board"',
        "    Execute Command    machine LoadPlatformDescription @platforms/cpus/stm32f103.repl",
        '    Execute Command    machine LoadPlatformDescriptionFromString """${board}"""',
        f"    Execute Command    sysbus LoadELF @{_posix(elf)}",
        "",
        "*** Test Cases ***",
    ]
    for check in checks:
        out.append(check.name)
        out.append("    Create Board")
        if isinstance(check, LedBlinkCheck):
            out += [
                f"    Create LED Tester    sysbus.gpioPort{check.port.upper()}.led{check.port.lower()}{check.pin}    defaultTimeout=2",
                f"    Assert LED Is Blinking    testDuration={check.duration}    onDuration={check.on}"
                f"    offDuration={check.off}    tolerance={check.tolerance}    pauseEmulation=true",
            ]
        else:
            out += [
                f"    Create Terminal Tester    sysbus.{check.peripheral}    timeout={check.timeout}",
                "    Start Emulation",
                f"    Wait For Line On Uart    {_robot_literal(check.expect)}    treatAsRegex=false",
            ]
        out.append("")
    return "\n".join(out) + "\n"


def _parse_robot_output(xml_path: Path, checks: list[Check]) -> list[dict[str, Any]]:
    by_name: dict[str, tuple[str, str]] = {}
    if xml_path.is_file():
        for test in ET.parse(xml_path).getroot().iter("test"):
            status = test.find("status")
            if status is not None:
                by_name[test.get("name", "")] = (status.get("status", "FAIL"), (status.text or "").strip())
    results = []
    for check in checks:
        status, message = by_name.get(check.name, ("FAIL", "test did not run"))
        results.append({"name": check.name, "status": "PASS" if status == "PASS" else "FAIL", "message": message[:500]})
    return results


def simulate(
    elf: Path,
    checks: list[Check],
    *,
    results_dir: Path | None = None,
    timeout: int = DEFAULT_TIMEOUT_SEC,
) -> SimResult:
    elf = Path(elf)
    if not checks:
        return SimResult("UNAVAILABLE", reason="no behavioural checks requested")
    if not elf.is_file():
        return SimResult("FAIL", reason=f"firmware not found: {elf}")
    renode = find_renode()
    if renode is None:
        return SimResult("UNAVAILABLE", reason="Renode not found (set CEA_RENODE_PATH)")
    python = find_test_python()
    if python is None:
        return SimResult("UNAVAILABLE", reason="no Python with robotframework/psutil/pyyaml (set CEA_RENODE_PYTHON)")

    out_dir = Path(results_dir) if results_dir else Path(tempfile.mkdtemp(prefix="cea-renode-"))
    out_dir.mkdir(parents=True, exist_ok=True)
    suite = out_dir / "behaviour.robot"
    suite.write_text(build_robot_suite(elf, checks), encoding="utf-8")
    cmd = [
        python,
        str(renode / "tests" / "run_tests.py"),
        "--css-file", str(renode / "tests" / "robot.css"),
        "--robot-framework-remote-server-full-directory", str(renode / "bin"),
        "-r", str(out_dir),
        str(suite),
    ]
    if os.name == "nt":
        cmd[2:2] = ["--exclude", "skip_windows"]
    try:
        proc = subprocess.run(cmd, cwd=out_dir, capture_output=True, stdin=subprocess.DEVNULL, text=True, timeout=timeout, check=False)
        log = (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        return SimResult("FAIL", reason=f"simulation timed out after {timeout}s", evidence={"suite": str(suite)})
    (out_dir / "runner.log").write_text(log, encoding="utf-8")

    results = _parse_robot_output(out_dir / "robot_output.xml", checks)
    status = "PASS" if all(r["status"] == "PASS" for r in results) else "FAIL"
    return SimResult(
        status,
        checks=results,
        reason=None if status == "PASS" else "; ".join(f"{r['name']}: {r['message']}" for r in results if r["status"] != "PASS"),
        evidence={"suite": str(suite), "report": str(out_dir / "report.html"), "log": str(out_dir / "runner.log")},
    )


def checks_from_spec(spec: dict[str, Any]) -> list[Check]:
    """Build checks from the ``simulate_firmware`` tool / benchmark oracle format::

        {"led": [{"pin": "PC13", "on_ms": 500, "off_ms": 500}],
         "uart": [{"peripheral": "usart1", "expect": "Hello"}]}
    """
    checks: list[Check] = []
    for item in spec.get("led") or []:
        pin = str(item.get("pin", "PC13")).upper().removeprefix("P")
        on_ms = float(item.get("on_ms") or item.get("half_period_ms") or 500)
        off_ms = float(item.get("off_ms") or on_ms)
        checks.append(
            LedBlinkCheck(
                port=pin[0],
                pin=int(pin[1:]),
                on=on_ms / 1000,
                off=off_ms / 1000,
                tolerance=float(item.get("tolerance", 0.05)),
                duration=max(4.0, 4 * (on_ms + off_ms) / 1000),
                active_low=bool(item.get("active_low", True)),
            )
        )
    for item in spec.get("uart") or []:
        checks.append(
            UartExpectCheck(
                peripheral=str(item.get("peripheral", "usart1")).lower(),
                expect=str(item.get("expect", "")),
                timeout=float(item.get("timeout_s", 3.0)),
            )
        )
    return checks


def _parse_led(spec: str) -> LedBlinkCheck:
    pin_part, _, period = spec.partition(":")
    half = float(period or 0.5)
    return LedBlinkCheck(port=pin_part[0].upper(), pin=int(pin_part[1:]), on=half, off=half)


def _parse_uart(spec: str) -> UartExpectCheck:
    peripheral, _, expect = spec.partition(":")
    return UartExpectCheck(peripheral=peripheral, expect=expect)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assert STM32F103 firmware behaviour in Renode")
    parser.add_argument("--elf", required=True, type=Path)
    parser.add_argument("--led", action="append", default=[], help="PORTPIN:half_period_s, e.g. C13:0.5")
    parser.add_argument("--uart", action="append", default=[], help="peripheral:text, e.g. usart1:Hello")
    parser.add_argument("--results-dir", type=Path)
    args = parser.parse_args(argv)
    checks: list[Check] = [*map(_parse_led, args.led), *map(_parse_uart, args.uart)]
    result = simulate(args.elf, checks, results_dir=args.results_dir)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
