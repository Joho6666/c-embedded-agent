from __future__ import annotations

from typing import Any

from app.core.types import FAIL, READ_ONLY, SUCCESS, UNAVAILABLE, envelope
from app.tools import serialutil


def list_serial_ports() -> dict[str, Any]:
    try:
        import serial  # noqa: F401
    except ImportError:
        return envelope(
            status=UNAVAILABLE,
            side_effect=READ_ONLY,
            available=False,
            reason="pyserial is not installed",
            ports=[],
        )
    ports = serialutil.list_ports()
    rows = []
    for p in ports:
        rows.append(
            {
                "port": p.get("device") or "",
                "device": p.get("device") or "",
                "description": p.get("description") or "",
                "hwid": p.get("hwid") or "",
                "status": "present",
            }
        )
    return envelope(
        status=SUCCESS,
        side_effect=READ_ONLY,
        available=True,
        ports=rows,
    )


def read_serial(
    *,
    port: str,
    baud: int = 115200,
    timeout: float = 8.0,
    max_lines: int = 80,
    expect: str | None = None,
) -> dict[str, Any]:
    if not port:
        return envelope(
            status=FAIL,
            side_effect=READ_ONLY,
            available=False,
            reason="port is required",
            lines=[],
        )
    try:
        serialutil.connect(port, baud)
    except ValueError as e:
        return envelope(status=FAIL, side_effect=READ_ONLY, available=False, reason=str(e), lines=[])
    except RuntimeError as e:
        unavailable = "pyserial" in str(e).lower()
        return envelope(
            status=UNAVAILABLE if unavailable else FAIL,
            side_effect=READ_ONLY,
            available=False,
            reason=str(e),
            lines=[],
        )
    except OSError as e:
        return envelope(status=FAIL, side_effect=READ_ONLY, available=False, reason=str(e), lines=[])
    try:
        lines = serialutil.wait_for(expect=expect, max_s=timeout, quiet=0.3)
    except OSError as e:
        return envelope(status=FAIL, side_effect=READ_ONLY, available=False, reason=str(e), lines=[])
    finally:
        try:
            serialutil.disconnect()
        except Exception:
            pass
    clipped = list(lines)[: max(1, int(max_lines))]
    return envelope(
        status=SUCCESS,
        side_effect=READ_ONLY,
        available=True,
        port=port,
        baud=baud,
        lines=clipped,
        fabricated=False,
    )
