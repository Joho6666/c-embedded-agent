from __future__ import annotations

import time
from collections import deque
from typing import Any

ALLOWED_BAUD = {9600, 115200}

_session: dict[str, Any] = {"port": None, "device": "", "baud": 115200, "lines": deque(maxlen=200)}


def list_ports() -> list[dict[str, Any]]:
    try:
        from serial.tools import list_ports
    except ImportError:
        return []
    out = []
    for p in list_ports.comports():
        out.append({"device": p.device, "description": p.description or "", "hwid": p.hwid or ""})
    return out


def connect(device: str, baud: int = 115200) -> dict[str, Any]:
    if baud not in ALLOWED_BAUD:
        raise ValueError("baud 仅支持 9600 或 115200")
    disconnect()
    try:
        import serial
    except ImportError as e:
        raise RuntimeError("未安装 pyserial") from e
    port = serial.Serial(device, baudrate=baud, timeout=0.2)
    _session["port"] = port
    _session["device"] = device
    _session["baud"] = baud
    _session["lines"].clear()
    return {"ok": True, "device": device, "baud": baud}


def disconnect() -> dict[str, str]:
    port = _session.get("port")
    if port is not None:
        try:
            port.close()
        except Exception:
            pass
    _session["port"] = None
    _session["device"] = ""
    return {"ok": "1"}


def status() -> dict[str, Any]:
    port = _session.get("port")
    return {
        "connected": bool(port and getattr(port, "is_open", False)),
        "device": _session.get("device") or "",
        "baud": _session.get("baud") or 115200,
        "lines": list(_session["lines"]),
    }


def read_available() -> list[dict[str, str]]:
    port = _session.get("port")
    if port is None:
        return list(_session["lines"])
    try:
        raw = port.read(1024)
    except Exception:
        raw = b""
    if raw:
        text = raw.decode("utf-8", errors="replace")
        for line in text.splitlines():
            if line:
                _session["lines"].append({"text": line})
    return list(_session["lines"])


def wait_for(expect: str | None = None, max_s: float = 8.0, quiet: float = 0.3) -> list[str]:
    """Adaptive serial wait: stop on expect token, else after a quiet period, else cap.

    No connected port → empty list (caller must not treat this as PASS).
    """
    if _session.get("port") is None:
        return [r.get("text") or "" for r in list(_session["lines"]) if r.get("text")]
    deadline = time.time() + max(0.2, float(max_s))
    quiet = max(0.05, float(quiet))
    last_n = 0
    last_change = time.time()
    needle = (expect or "").strip()
    while time.time() < deadline:
        rows = read_available()
        lines = [r.get("text") or "" for r in rows if r.get("text")]
        joined = "\n".join(lines)
        if needle and needle.lower() in joined.lower():
            return lines
        if len(lines) != last_n:
            last_n = len(lines)
            last_change = time.time()
        elif lines and (time.time() - last_change) >= quiet:
            return lines
        time.sleep(0.2)
    rows = read_available()
    return [r.get("text") or "" for r in rows if r.get("text")]
