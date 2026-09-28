"""Real STM32F103 board through an ST-Link (OpenOCD) and a USB-serial port.

NOT YET VALIDATED ON HARDWARE: the code path mirrors the virtual board so the
tools and skills above it do not change, but ``info()["validated"]`` stays
False until it has been run against a physical Blue Pill. Nothing here reports
success without OpenOCD's own ``verify`` result or bytes actually read from the
serial port.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any

from app.device.base import GPIO_IDR, GPIO_ODR, STM32F1_GPIO_BASE, DeviceBackend, DeviceError, parse_pin
from app.tools.flash import ALLOWED_INTERFACE, ALLOWED_TARGET, detect_chip_id


class ProbeBluePill(DeviceBackend):
    kind = "hardware"
    evidence = "HARDWARE"

    def __init__(self, *, serial_device: str | None = None, baud: int = 115200) -> None:
        super().__init__()
        self.serial_device = serial_device or os.environ.get("CEA_SERIAL_PORT") or None
        self.baud = baud
        self.port: Any = None
        self.firmware: Path | None = None
        self.lock = threading.RLock()

    def available(self) -> tuple[bool, str | None]:
        if not shutil.which("openocd"):
            return False, "openocd not on PATH"
        chip = detect_chip_id()
        if chip.get("family") != "STM32F1":
            return False, "no STM32F1 target detected through ST-Link"
        return True, None

    def open(self) -> None:
        if self.port is not None or not self.serial_device:
            return
        try:
            import serial
        except ImportError as e:
            raise DeviceError("pyserial not installed") from e
        self.port = serial.Serial(self.serial_device, baudrate=self.baud, timeout=0)

    def _openocd(self, script: str, timeout: int = 60) -> subprocess.CompletedProcess[str]:
        exe = shutil.which("openocd")
        if not exe:
            raise DeviceError("openocd not on PATH")
        return subprocess.run(
            [exe, "-f", ALLOWED_INTERFACE, "-f", ALLOWED_TARGET, "-c", script],
            capture_output=True, stdin=subprocess.DEVNULL, text=True, timeout=timeout, check=False, shell=False,
        )

    def flash(self, elf: Path) -> dict[str, Any]:
        elf = Path(elf).resolve()
        if not elf.is_file():
            raise DeviceError(f"firmware not found: {elf}")
        self.open()
        with self.lock:
            proc = self._openocd(f"program {elf.as_posix()} verify reset exit")
        output = (proc.stdout or "") + (proc.stderr or "")
        ok = proc.returncode == 0 and "verified" in output.lower()
        if ok:
            self.firmware = elf
        return {"ok": ok, "evidence": self.evidence, "firmware": str(elf), "output": output[-3000:]}

    def reset(self) -> dict[str, Any]:
        with self.lock:
            proc = self._openocd("init; reset run; shutdown", timeout=20)
        return {"ok": proc.returncode == 0, "output": ((proc.stdout or "") + (proc.stderr or ""))[-1500:]}

    def tick(self) -> None:
        if self.port is None:
            return
        try:
            data = self.port.read(4096)
        except Exception:
            return
        if data:
            self.emit_serial("usart1", data.decode("utf-8", "replace"))

    def write_serial(self, text: str, channel: str = "usart1") -> dict[str, Any]:
        if self.port is None:
            return {"ok": False, "reason": "no serial port configured (CEA_SERIAL_PORT)"}
        self.port.write(text.encode("utf-8"))
        return {"ok": True, "channel": channel, "bytes": len(text.encode("utf-8"))}

    def read_pins(self, pins: list[str]) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for pin in pins:
            try:
                port, number = parse_pin(pin)
            except (ValueError, IndexError) as e:
                out[pin] = {"level": None, "reason": str(e)}
                continue
            base = STM32F1_GPIO_BASE[port]
            with self.lock:
                proc = self._openocd(f"init; mdw {base + GPIO_ODR:#x}; mdw {base + GPIO_IDR:#x}; shutdown", timeout=20)
            words = [line.split(":")[1].split()[0] for line in (proc.stderr + proc.stdout).splitlines() if line.startswith("0x") and ":" in line]
            if len(words) < 2:
                out[f"P{port}{number}"] = {"level": None, "reason": "could not read GPIO registers"}
                continue
            odr, idr = int(words[0], 16), int(words[1], 16)
            out[f"P{port}{number}"] = {"output": bool(odr >> number & 1), "input": bool(idr >> number & 1)}
        return out

    def info(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "evidence": self.evidence,
            "board": "STM32F103 via ST-Link",
            "serial_device": self.serial_device,
            "running": self.firmware is not None,
            "validated": False,
            "note": "hardware path not yet validated on a physical board",
        }

    def close(self) -> None:
        if self.port is not None:
            try:
                self.port.close()
            except Exception:
                pass
            self.port = None
