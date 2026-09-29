"""Renode simulation adapter.

Runs a firmware ELF on a Renode-emulated MCU and captures UART output via a
file backend — the Level-2 (Simulation) evidence path when no hardware is
attached.

Renode is discovered from (in order): `CEA_RENODE_PATH` env var, `renode` /
`Renode.exe` on PATH, and the vendored location `~/tools/renode-portable/renode_*/
bin/Renode.exe`. SPIKE status: SUPPORTED for STM32F103 after the real run
documented in docs/RENODE_SPIKE.md.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from app.hardware.simulation.base import SimulationAdapter, _evidence

DEFAULT_PLATFORM = "platforms/cpus/stm32f103.repl"
DEFAULT_UART = "usart1"


class RenodePathError(RuntimeError):
    pass


def find_renode() -> Path | None:
    env = os.environ.get("CEA_RENODE_PATH")
    if env and Path(env).is_file():
        return Path(env)
    home = Path.home()
    vendored = sorted(
        (home / "tools" / "renode-portable").glob("renode_*/bin/Renode.exe")
    )
    if vendored:
        return vendored[-1]
    for name in ("Renode.exe", "renode"):
        found = _which(name)
        if found:
            return found
    return None


def _which(name: str) -> str | None:
    import shutil

    return shutil.which(name)


class RenodeAdapter(SimulationAdapter):
    id = "renode"
    label = "Renode"
    adapter_status = "SUPPORTED"  # verified by the real spike; see docs/RENODE_SPIKE.md

    def __init__(self, timeout_s: float = 20.0) -> None:
        self.timeout_s = timeout_s
        self._proc: subprocess.Popen[str] | None = None

    def detect(self) -> dict[str, Any]:
        path = find_renode()
        version = None
        if path:
            try:
                r = subprocess.run(
                    [str(path), "--version"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
                m = re.search(r"(\d+\.\d+\.\d+)", (r.stdout or "") + (r.stderr or ""))
                version = m.group(1) if m else "unknown"
            except (OSError, subprocess.TimeoutExpired):
                version = None
        return {
            "available": path is not None and version is not None,
            "adapterStatus": self.adapter_status if path else "NOT_INSTALLED",
            "path": str(path) if path else None,
            "version": version,
            "status": "UNKNOWN",
            "reason": None if path else "Renode not installed (CEA_RENODE_PATH or ~/tools/renode-portable)",
        }

    def _write_script(self, workdir: Path, elf: Path, platform: str, uart: str, uart_log: Path) -> Path:
        script = workdir / "cea-sim.resc"
        script.write_text(
            "\n".join(
                [
                    "using sysbus",
                    'mach create "cea-sim"',
                    f"machine LoadPlatformDescription @{platform}",
                    f"sysbus.{uart} CreateFileBackend @{uart_log.as_posix()}",
                    f"sysbus LoadELF @{elf.as_posix()}",
                    "start",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return script

    def run(
        self,
        elf_path: str,
        *,
        platform: str | None = None,
        uart_output_log: str | None = None,
        expect: str | None = None,
        timeout_s: float | None = None,
        uart: str = DEFAULT_UART,
    ) -> dict[str, Any]:
        renode = find_renode()
        if not renode:
            return {
                "available": False,
                "status": "UNAVAILABLE",
                "reason": "Renode not installed — simulation NOT_RUN (never faked)",
                "evidence": _evidence("firmware simulated in Renode", False, "renode", "tool missing"),
            }
        elf = Path(elf_path)
        if not elf.is_file():
            return {"available": True, "status": "FAIL", "reason": f"ELF not found: {elf}"}
        workdir = elf.parent / "renode-run"
        workdir.mkdir(parents=True, exist_ok=True)
        uart_log = Path(uart_output_log) if uart_output_log else workdir / "uart.log"
        if uart_log.exists():
            uart_log.unlink()
        platform = platform or DEFAULT_PLATFORM
        script = self._write_script(workdir, elf, platform, uart, uart_log)

        env_root = renode.parent.parent if renode.name.lower().endswith(".exe") else renode.parent
        # Windows portable: <pkg>/bin/Renode.exe → pkg; Linux portable: <pkg>/renode → pkg
        try:
            self._proc = subprocess.Popen(
                [str(renode), "--console", "--disable-xwt", "-e", f"include @{script.as_posix()}"],
                cwd=str(env_root),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
            )
        except OSError as e:
            return {"available": True, "status": "UNAVAILABLE", "reason": f"renode failed to start: {e}"}

        limit = timeout_s or self.timeout_s
        matched = False
        saw_output = False
        deadline = time.time() + limit

        def read_log() -> str | None:
            try:
                return uart_log.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return None  # Renode holds the log open on Windows; retry later

        try:
            while time.time() < deadline:
                text = read_log()
                if text is not None:
                    if text.strip():
                        saw_output = True
                    if expect and expect in text:
                        matched = True
                        break
                    if not expect and text.strip():
                        break
                time.sleep(0.25)
        finally:
            self.stop()

        # Final read after Renode released the file handle
        text = read_log()
        lines = [
            ln for ln in (text or "").splitlines() if ln.strip()
        ][:500]
        matched = matched or bool(expect and expect in (text or ""))
        saw_output = saw_output or bool(lines)
        evidence = _evidence(
            "firmware executed in Renode emulator; UART output captured",
            matched if expect else saw_output or bool(lines),
            "renode",
            {"expect": expect, "matched": matched, "platform": platform},
        )
        return {
            "available": True,
            "status": "SUCCESS" if (matched if expect else (saw_output or bool(lines))) else "FAIL",
            "uartLines": lines,
            "expectMatch": matched if expect else None,
            "platform": platform,
            "uart": uart,
            "evidence": evidence,
        }

    def stop(self) -> dict[str, Any]:
        if self._proc is not None:
            try:
                if self._proc.stdin:
                    self._proc.stdin.write("q\n")
                    self._proc.stdin.flush()
                self._proc.wait(timeout=10)
            except Exception:  # noqa: BLE001 — best-effort teardown
                self._proc.kill()
            self._proc = None
        return {"available": True, "status": "SUCCESS", "stopped": True}
