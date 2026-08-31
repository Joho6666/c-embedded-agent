from __future__ import annotations

from typing import Any

ALLOWED_BAUD = {9600, 115200}


def list_ports() -> list[dict[str, Any]]:
    try:
        from serial.tools import list_ports
    except ImportError:
        return []
    out = []
    for p in list_ports.comports():
        out.append({"device": p.device, "description": p.description or "", "hwid": p.hwid or ""})
    return out


def open_port(device: str, baud: int = 115200):
    if baud not in ALLOWED_BAUD:
        raise ValueError("baud 仅支持 9600 或 115200")
    try:
        import serial
    except ImportError as e:
        raise RuntimeError("未安装 pyserial") from e
    return serial.Serial(device, baudrate=baud, timeout=1)
