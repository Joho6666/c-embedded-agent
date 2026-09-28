"""Long-lived device session: one-click flash and an always-current board state.

The service owns one backend (virtual Blue Pill or real probe), advances it from
a background thread, assembles serial output into lines, and records build and
flash events. ``status()`` is the "latest state" view: what firmware is on the
board, whether it built, what it printed, what the LED/pins are doing, and which
kind of evidence all of that is.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.device.base import DeviceBackend, DeviceError
from app.tools.gcc_parser import parse_gcc_output
from app.tools.toolchain import prepend_toolchain_path

SERIAL_HISTORY = 2000
EVENT_HISTORY = 200
SIZE_RE = re.compile(r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+\d+\s+[0-9a-f]+\s+\S*firmware\.elf", re.MULTILINE)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def resolve_project(project: str | None) -> Path:
    root = Path(project or os.environ.get("CEA_PROJECT") or os.getcwd()).expanduser().resolve()
    if not (root / "Makefile").is_file():
        raise DeviceError(f"not a Makefile firmware project: {root}")
    return root


def select_backend(preference: str | None = None) -> DeviceBackend:
    from app.device.probe_board import ProbeBluePill
    from app.device.virtual_board import VirtualBluePill

    choice = (preference or os.environ.get("CEA_DEVICE") or "auto").lower()
    if choice == "hardware":
        return ProbeBluePill()
    if choice == "virtual":
        return VirtualBluePill()
    probe = ProbeBluePill()
    return probe if probe.available()[0] else VirtualBluePill()


class DeviceService:
    def __init__(self, backend: DeviceBackend | None = None, *, pace_interval_s: float = 0.05) -> None:
        self.backend = backend or select_backend()
        self.backend.sink = self._on_serial
        self.pace_interval_s = pace_interval_s
        self.lock = threading.RLock()
        self.serial: deque[dict[str, Any]] = deque(maxlen=SERIAL_HISTORY)
        self.events: deque[dict[str, Any]] = deque(maxlen=EVENT_HISTORY)
        self._partial: dict[str, str] = {}
        self._seq = 0
        self.generation = 0  # increments on every flash; lines are tagged with it
        self.project: Path | None = None
        self.last_build: dict[str, Any] | None = None
        self.last_flash: dict[str, Any] | None = None
        self._paused = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------ plumbing

    def _event(self, kind: str, **data: Any) -> dict[str, Any]:
        event = {"time": _now(), "kind": kind, **data}
        self.events.append(event)
        return event

    def _on_serial(self, channel: str, chunk: str) -> None:
        with self.lock:
            # Drop CR entirely: a "\r\n" split across chunks must not yield an empty line.
            buf = self._partial.get(channel, "") + chunk.replace("\r", "")
            *lines, rest = buf.split("\n")
            self._partial[channel] = rest[-4096:]
            vtime = getattr(self.backend, "virtual_time", None)
            for text in lines:
                self._seq += 1
                self.serial.append(
                    {"seq": self._seq, "channel": channel, "text": text, "generation": self.generation,
                     "wall": _now(), "virtual_s": round(vtime, 3) if vtime is not None else None}
                )

    def _pace(self) -> None:
        while not self._stop.is_set():
            if not self._paused.is_set():
                try:
                    self.backend.tick()
                except Exception as e:  # noqa: BLE001 - keep the session alive, surface the error
                    self._event("backend_error", error=str(e)[:300])
                    self._stop.wait(1.0)
            self._stop.wait(self.pace_interval_s)

    def _ensure_running(self) -> None:
        self.backend.open()
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = threading.Thread(target=self._pace, daemon=True, name="cea-device-pace")
            self._thread.start()

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self.backend.close()

    # ------------------------------------------------------------ build

    def build(self, project: str | None = None) -> dict[str, Any]:
        root = resolve_project(project)
        self.project = root
        prepend_toolchain_path()
        make = shutil.which("make")
        if not make or not shutil.which("arm-none-eabi-gcc"):
            result = {"success": False, "status": "UNAVAILABLE", "reason": "arm-none-eabi-gcc or make not found"}
            self.last_build = result
            self._event("build", success=False, reason=result["reason"])
            return result
        t0 = time.perf_counter()
        proc = subprocess.run([make, "-j4"], cwd=root, capture_output=True, stdin=subprocess.DEVNULL, text=True, timeout=300, check=False)
        combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
        diagnostics = parse_gcc_output(combined)
        elf = root / "firmware.elf"
        size = SIZE_RE.search(combined)
        result = {
            "success": proc.returncode == 0 and elf.is_file(),
            "project": str(root),
            "seconds": round(time.perf_counter() - t0, 2),
            "errors": [d for d in diagnostics if d.get("severity") == "error"][:15],
            "warnings": len([d for d in diagnostics if d.get("severity") == "warning"]),
            "memory": {"flash_bytes": int(size.group(1)) + int(size.group(2)), "ram_bytes": int(size.group(2)) + int(size.group(3))} if size else None,
            "firmware": str(elf) if elf.is_file() else None,
            "log_tail": combined[-1500:] if proc.returncode != 0 else "",
        }
        self.last_build = result | {"time": _now()}
        self._event("build", success=result["success"], errors=len(result["errors"]))
        return result

    # ------------------------------------------------------------ one-click flash

    def flash(
        self,
        project: str | None = None,
        *,
        expect: str | None = None,
        observe_s: float = 2.0,
        build: bool = True,
    ) -> dict[str, Any]:
        """Build (optional) -> flash -> run -> watch serial for ``expect``."""
        root = resolve_project(project)
        build_result = self.build(str(root)) if build else self.last_build
        if build and not build_result.get("success"):
            self.last_flash = {"success": False, "stage": "build", "time": _now()}
            return {"success": False, "stage": "build", "build": build_result}
        elf = root / "firmware.elf"
        digest = hashlib.sha256(elf.read_bytes()).hexdigest()[:12] if elf.is_file() else None
        self._paused.set()
        try:
            self._ensure_running()
            with self.lock:
                self.generation += 1
                self._partial.clear()
                generation = self.generation
            flashed = self.backend.flash(elf)
            if not flashed.get("ok"):
                self.last_flash = {"success": False, "stage": "flash", "time": _now(), "detail": flashed}
                self._event("flash", success=False)
                return {"success": False, "stage": "flash", "flash": flashed, "build": build_result}
            advance = getattr(self.backend, "advance", None)
            if callable(advance):
                advance(observe_s)  # virtual: observe exactly observe_s of board time
            else:
                deadline = time.time() + observe_s  # hardware: observe wall time
                while time.time() < deadline:
                    self.backend.tick()
                    time.sleep(0.05)
            time.sleep(0.2)  # let socket readers deliver the last bytes
        finally:
            self._paused.clear()
        lines = [entry["text"] for entry in self.serial if entry["generation"] == generation]
        found = None if expect is None else any(expect in line for line in lines)
        self.last_flash = {
            "success": True,
            "time": _now(),
            "firmware": str(elf),
            "sha256_12": digest,
            "generation": generation,
            "evidence": self.backend.evidence,
            "expect": expect,
            "expect_found": found,
        }
        self._event("flash", success=True, sha=digest, expect_found=found)
        return {
            "success": found is not False,
            "stage": "observe" if found is False else "done",
            "evidence": self.backend.evidence,
            "observed_s": observe_s,
            "serial": lines[-40:],
            "expect": expect,
            "expect_found": found,
            "build": {k: build_result.get(k) for k in ("success", "memory", "warnings", "seconds")} if build_result else None,
            "firmware_sha256_12": digest,
        }

    # ------------------------------------------------------------ live state

    def serial_tail(self, limit: int = 50, since_seq: int = 0, current_firmware_only: bool = True) -> dict[str, Any]:
        with self.lock:
            rows = [
                e for e in self.serial
                if e["seq"] > since_seq and (not current_firmware_only or e["generation"] == self.generation)
            ]
        return {"lines": rows[-limit:], "last_seq": self._seq, "evidence": self.backend.evidence}

    def write_serial(self, text: str, channel: str = "usart1") -> dict[str, Any]:
        self._ensure_running()
        result = self.backend.write_serial(text, channel)
        self._event("serial_write", channel=channel, ok=result.get("ok"))
        return result

    def read_pins(self, pins: list[str]) -> dict[str, Any]:
        if self.generation == 0:
            return {"pins": {}, "reason": "no firmware flashed yet"}
        return {"pins": self.backend.read_pins(pins), "evidence": self.backend.evidence}

    def status(self, pins: list[str] | None = None) -> dict[str, Any]:
        info = self.backend.info()
        state: dict[str, Any] = {
            "device": info,
            "project": str(self.project) if self.project else None,
            "last_build": self.last_build,
            "last_flash": self.last_flash,
            "serial_tail": [e["text"] for e in self.serial_tail(limit=10)["lines"]],
            "recent_events": list(self.events)[-8:],
        }
        if self.generation:
            try:
                state["pins"] = self.backend.read_pins(pins or ["PC13"])
            except Exception as e:  # noqa: BLE001
                state["pins"] = {"error": str(e)[:200]}
        return state
