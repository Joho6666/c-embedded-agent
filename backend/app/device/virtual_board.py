"""Persistent virtual Blue Pill on Renode.

One Renode process stays up for the whole session. Firmware is reflashed with
``machine Reset`` + ``LoadELF`` (no restart), time advances in small ``RunFor``
slices from the service thread, USART output arrives as a raw byte stream over
server-socket terminals, and pins are read from the GPIO ODR/IDR registers.

Renode is controlled through its Robot Framework XML-RPC server
(``--robot-server-port``): request/response per command, unlike the telnet
monitor which garbles input during negotiation.
"""

from __future__ import annotations

import socket
import subprocess
import tempfile
import threading
import time
import xmlrpc.client
from pathlib import Path
from typing import Any

from app.device.base import GPIO_IDR, GPIO_ODR, STM32F1_GPIO_BASE, DeviceBackend, DeviceError, parse_pin
from app.sim.renode import LedBlinkCheck, _board_description, find_renode

UART_CHANNELS = ("usart1", "usart2")
BOARD_LED = ("C", 13)  # Blue Pill user LED, active-low


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class VirtualBluePill(DeviceBackend):
    kind = "virtual"
    evidence = "SIMULATED"

    def __init__(self, *, slice_s: float = 0.25) -> None:
        super().__init__()
        self.slice_s = slice_s
        self.proc: subprocess.Popen[bytes] | None = None
        self.rpc: xmlrpc.client.ServerProxy | None = None
        self.lock = threading.RLock()
        self.virtual_time = 0.0
        self.firmware: Path | None = None
        self.running = False
        self._uart: dict[str, socket.socket] = {}
        self._readers: list[threading.Thread] = []
        self._closing = False

    # ------------------------------------------------------------ lifecycle

    def available(self) -> tuple[bool, str | None]:
        root = find_renode()
        if root is None:
            return False, "Renode not found (set CEA_RENODE_PATH)"
        if not self._renode_exe(root).is_file():
            return False, f"Renode executable missing under {root}"
        return True, None

    @staticmethod
    def _renode_exe(root: Path) -> Path:
        for candidate in (root / "bin" / "Renode.exe", root / "renode", root / "bin" / "renode"):
            if candidate.is_file():
                return candidate
        return root / "bin" / "Renode.exe"

    def open(self) -> None:
        if self.proc is not None:
            return
        ok, reason = self.available()
        if not ok:
            raise DeviceError(reason or "virtual board unavailable")
        port = _free_port()
        exe = self._renode_exe(find_renode())  # type: ignore[arg-type]
        self.proc = subprocess.Popen(
            [str(exe), "--disable-gui", "--robot-server-port", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
        self.rpc = self._connect_rpc(port)
        board = Path(tempfile.gettempdir()) / f"cea-bluepill-{port}.repl"
        board.write_text("\n".join(_board_description([LedBlinkCheck(port=BOARD_LED[0], pin=BOARD_LED[1])])) + "\n", encoding="utf-8")
        self._cmd('mach create "bluepill"')
        self._cmd("machine LoadPlatformDescription @platforms/cpus/stm32f103.repl")
        self._cmd(f"machine LoadPlatformDescription @{board.as_posix()}")
        for channel in UART_CHANNELS:
            uart_port = _free_port()
            self._cmd(f'emulation CreateServerSocketTerminal {uart_port} "{channel}term" false')
            self._cmd(f"connector Connect sysbus.{channel} {channel}term")
            sock = socket.create_connection(("127.0.0.1", uart_port), timeout=5)
            sock.settimeout(0.2)
            self._uart[channel] = sock
            reader = threading.Thread(target=self._read_uart, args=(channel, sock), daemon=True, name=f"uart-{channel}")
            reader.start()
            self._readers.append(reader)

    def _connect_rpc(self, port: int) -> xmlrpc.client.ServerProxy:
        deadline = time.time() + 60
        last: Exception | None = None
        while time.time() < deadline:
            if self.proc is not None and self.proc.poll() is not None:
                raise DeviceError(f"Renode exited early with code {self.proc.returncode}")
            # Renode's HTTP listener answers 400 to 127.0.0.1 Host headers; use localhost.
            rpc = xmlrpc.client.ServerProxy(f"http://localhost:{port}/", allow_none=True)
            try:
                rpc.get_keyword_names()
                return rpc
            except (OSError, xmlrpc.client.ProtocolError) as e:
                last = e
                time.sleep(0.4)
        raise DeviceError(f"Renode control server unreachable: {last}")

    def close(self) -> None:
        self._closing = True
        with self.lock:
            for sock in self._uart.values():
                try:
                    sock.close()
                except OSError:
                    pass
            self._uart.clear()
            if self.rpc is not None:
                try:
                    self.rpc.stop_remote_server()
                except Exception:
                    pass
            if self.proc is not None:
                try:
                    self.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
            self.proc = None
            self.rpc = None
            self.running = False

    # ------------------------------------------------------------ control

    def _cmd(self, command: str) -> str:
        if self.rpc is None:
            raise DeviceError("virtual board not open")
        with self.lock:
            result = self.rpc.run_keyword("ExecuteCommand", [command])
        if result.get("status") != "PASS":
            raise DeviceError(f"{command}: {str(result.get('error'))[:300]}")
        return str(result.get("return") or "").strip()

    def flash(self, elf: Path) -> dict[str, Any]:
        elf = Path(elf).resolve()
        if not elf.is_file():
            raise DeviceError(f"firmware not found: {elf}")
        self.open()
        with self.lock:
            self.running = False
            self._cmd("machine Reset")
            self._cmd(f"sysbus LoadELF @{elf.as_posix()}")
            self.firmware = elf
            self.running = True
        return {"ok": True, "evidence": self.evidence, "firmware": str(elf)}

    def reset(self) -> dict[str, Any]:
        if self.firmware is None:
            return {"ok": False, "reason": "no firmware loaded"}
        return self.flash(self.firmware)

    def tick(self) -> None:
        if not self.running or self.rpc is None:
            return
        with self.lock:
            self._cmd(f'emulation RunFor "{self.slice_s:.3f}"')
            self.virtual_time += self.slice_s

    def advance(self, seconds: float) -> None:
        """Advance virtual time synchronously (used by one-click flash to observe boot output)."""
        steps = max(1, int(round(seconds / self.slice_s)))
        for _ in range(steps):
            self.tick()

    # ------------------------------------------------------------ I/O

    def _read_uart(self, channel: str, sock: socket.socket) -> None:
        while not self._closing:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                return
            if not chunk:
                return
            self.emit_serial(channel, chunk.decode("utf-8", "replace"))

    def write_serial(self, text: str, channel: str = "usart1") -> dict[str, Any]:
        sock = self._uart.get(channel)
        if sock is None:
            return {"ok": False, "reason": f"no such channel: {channel}"}
        sock.sendall(text.encode("utf-8"))
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
            odr = int(self._cmd(f"sysbus ReadDoubleWord {base + GPIO_ODR:#x}"), 16)
            idr = int(self._cmd(f"sysbus ReadDoubleWord {base + GPIO_IDR:#x}"), 16)
            entry: dict[str, Any] = {"output": bool(odr >> number & 1), "input": bool(idr >> number & 1)}
            if (port, number) == BOARD_LED:
                led = self._cmd(f"sysbus.gpioPort{port}.led{port.lower()}{number} State")
                entry["board_led_on"] = led.strip().lower() == "true"
            out[f"P{port}{number}"] = entry
        return out

    def info(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "evidence": self.evidence,
            "board": "Blue Pill (STM32F103C8T6) on Renode",
            "running": self.running,
            "virtual_time_s": round(self.virtual_time, 3),
            "uart_channels": list(self._uart),
            "validated": True,
        }
