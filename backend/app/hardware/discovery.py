"""Local hardware discovery.

Builds a Hardware Discovery Report from what the host can actually observe:
debug probes (st-info --probe, J-Link CLI presence), USB serial ports with
VID/PID decoding, and — when OpenOCD is available — an SWD chip-id read.

Rules:
- Fuzzy USB information yields a platform *hint* only. `mcu` stays UNKNOWN
  until an SWD chip-id read confirms at least the family.
- A missing tool is `not_installed`; an absent device is `not_detected`.
  Neither is ever reported as Connected.
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app.config.settings import settings
from app.hardware.models import normalize_device

# (vid, pid) -> (name, kind, platformHint)
USB_TABLE: dict[tuple[int, int], tuple[str, str, str | None]] = {
    # ST-Link family
    (0x0483, 0x3744): ("ST-LINK/V1", "debug-probe", "stm32"),
    (0x0483, 0x3748): ("ST-LINK/V2", "debug-probe", "stm32"),
    (0x0483, 0x374A): ("ST-LINK/V2-1", "debug-probe", "stm32"),
    (0x0483, 0x374B): ("ST-LINK/V2-1", "debug-probe", "stm32"),
    (0x0483, 0x374F): ("STLINK-V3", "debug-probe", "stm32"),
    (0x0483, 0x374E): ("STLINK-V3", "debug-probe", "stm32"),
    # SEGGER J-Link
    (0x1366, 0x0101): ("SEGGER J-Link", "debug-probe", None),
    (0x1366, 0x0105): ("SEGGER J-Link", "debug-probe", None),
    (0x1366, 0x1015): ("SEGGER J-Link", "debug-probe", None),
    # ESP USB-JTAG / serial
    (0x303A, 0x1001): ("ESP32-Sx USB-JTAG", "debug-probe", "esp32"),
    (0x303A, 0x1002): ("ESP USB-Serial-JTAG", "usb-serial", "esp32"),
    # USB-UART bridges
    (0x1A86, 0x7523): ("CH340", "usb-serial", None),
    (0x1A86, 0x55D4): ("CH9102", "usb-serial", None),
    (0x10C4, 0xEA60): ("CP210x", "usb-serial", None),
    (0x10C4, 0xEA61): ("CP210x", "usb-serial", None),
    (0x0403, 0x6001): ("FT232", "usb-serial", None),
    (0x0403, 0x6010): ("FT2232", "debug-probe", None),
    (0x0403, 0x6014): ("FT232H", "debug-probe", None),
    # Raspberry Pi debug probe / Pico
    (0x2E8A, 0x0003): ("Raspberry Pi Pico (CMSIS-DAP)", "debug-probe", None),
    (0x2E8A, 0x0009): ("picoprobe", "debug-probe", None),
}

_VIDPID_RE = re.compile(r"VID:PID\s*=\s*([0-9A-Fa-f]{4}):([0-9A-Fa-f]{4})")
_SER_RE = re.compile(r"SER\s*=\s*([^\s]+)")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def stlink_probe() -> dict[str, Any]:
    from app.tools.detect import _probe_stlink

    return _probe_stlink()


def _decode_serial_ports(
    list_ports_fn: Callable[[], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    ports: list[dict[str, Any]] = []
    for p in list_ports_fn():
        hwid = str(p.get("hwid") or "")
        m = _VIDPID_RE.search(hwid)
        vid = int(m.group(1), 16) if m else None
        pid = int(m.group(2), 16) if m else None
        entry = USB_TABLE.get((vid, pid)) if vid is not None else None
        ser = _SER_RE.search(hwid)
        ports.append(
            {
                "device": p.get("device") or "",
                "description": p.get("description") or "",
                "vid": f"{vid:04X}" if vid is not None else None,
                "pid": f"{pid:04X}" if pid is not None else None,
                "usbName": entry[0] if entry else None,
                "kind": entry[1] if entry else None,
                "platformHint": entry[2] if entry else None,
                "serialNumber": ser.group(1) if ser else None,
            }
        )
    return ports


def _probe_report() -> list[dict[str, Any]]:
    probes: list[dict[str, Any]] = []

    st = stlink_probe()
    probes.append(
        {
            "id": "stlink",
            "label": "ST-LINK",
            "tool": "st-info",
            "toolInstalled": bool(st.get("installed")),
            "presence": "connected" if st.get("connected") else ("not_detected" if st.get("installed") else "not_installed"),
            "detail": st.get("version") or st.get("detail"),
        }
    )

    jlink = shutil.which("JLink.exe") or shutil.which("JLinkExe")
    probes.append(
        {
            "id": "jlink",
            "label": "SEGGER J-Link",
            "tool": "JLink",
            "toolInstalled": bool(jlink),
            "presence": "not_detected" if jlink else "not_installed",
            "detail": jlink,
        }
    )

    probes.append(
        {
            "id": "cmsis-dap",
            "label": "CMSIS-DAP",
            "tool": None,
            "toolInstalled": False,
            "presence": "not_detected",
            "detail": "No CMSIS-DAP probe API integrated yet — USB VID/PID may still show a probe below",
        }
    )

    probes.append(
        {
            "id": "esp-usb-jtag",
            "label": "ESP USB-JTAG",
            "tool": "esptool",
            "toolInstalled": bool(shutil.which("esptool") or shutil.which("esptool.py")),
            "presence": "not_detected",
            "detail": None,
        }
    )
    return probes


def identify_target() -> dict[str, Any]:
    """SWD chip-id read via OpenOCD. Family-level evidence only.

    Even a confirmed STM32F1 chip-id does not distinguish C8T6 from CB——
    the exact model stays UNKNOWN unless a manual profile records it.
    """
    from app.tools.flash import detect_chip_id

    chip = detect_chip_id()
    if not chip.get("available"):
        return {
            "available": False,
            "reason": "OpenOCD not installed — install OpenOCD with ST-Link support for SWD chip-id",
            "family": None,
        }
    family = chip.get("family")
    return {
        "available": True,
        "family": family,
        "exactMcu": "UNKNOWN",
        "evidence": "swd-chip-id-family" if family else None,
        "output": (chip.get("output") or "")[-800:],
    }


def discover(
    list_ports_fn: Callable[[], list[dict[str, Any]]] | None = None,
    stlink_fn: Callable[[], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run one discovery pass. Deterministic given injected inputs (tests)."""
    if list_ports_fn is None:
        from app.tools.serialutil import list_ports as list_ports_fn  # type: ignore[no-redef]
    if stlink_fn is None:
        stlink_fn = stlink_probe

    probes = _probe_report()
    ports = _decode_serial_ports(list_ports_fn)

    devices: list[dict[str, Any]] = []
    seen_ports: set[str] = set()

    # Debug probes first
    for probe in probes:
        if probe["id"] == "stlink" and probe["presence"] == "connected":
            devices.append(
                normalize_device(
                    {
                        "id": "probe-stlink",
                        "platformId": "unknown",
                        "platformHint": "stm32",
                        "board": "UNKNOWN",
                        "mcu": "UNKNOWN",
                        "debugProbe": "ST-Link",
                        "capabilities": ["debug-probe"],
                        "status": "ONLINE",
                        "source": "discovery",
                    }
                )
            )

    # USB serial ports
    for port in ports:
        if not port["device"] or port["device"] in seen_ports:
            continue
        seen_ports.add(port["device"])
        if port["kind"] == "usb-serial":
            devices.append(
                normalize_device(
                    {
                        "id": f"serial-{port['device'].lower()}",
                        "platformId": "unknown",
                        "platformHint": port["platformHint"],
                        "board": "UNKNOWN",
                        "mcu": "UNKNOWN",
                        "serialPort": port["device"],
                        "serialNumber": port["serialNumber"],
                        "capabilities": ["usb-serial"],
                        "status": "ONLINE",
                        "source": "discovery",
                    }
                )
            )
        elif port["kind"] == "debug-probe" and not any(
            d["debugProbe"] == port["usbName"] for d in devices
        ):
            devices.append(
                normalize_device(
                    {
                        "id": f"probe-{port['usbName'].lower().replace(' ', '-')}-{port['device'].lower()}",
                        "platformId": "unknown",
                        "platformHint": port["platformHint"],
                        "board": "UNKNOWN",
                        "mcu": "UNKNOWN",
                        "debugProbe": port["usbName"],
                        "serialNumber": port["serialNumber"],
                        "capabilities": ["debug-probe"],
                        "status": "ONLINE",
                        "source": "discovery",
                    }
                )
            )

    report = {
        "generatedAt": _now(),
        "host": _host(),
        "probes": probes,
        "serialPorts": ports,
        "devices": devices,
        "exactMcu": "UNKNOWN",
        "honesty": {
            "mcuClaimPolicy": "mcu stays UNKNOWN until SWD chip-id confirms the family",
            "usbHintIsNotIdentity": True,
        },
        "nextSteps": _next_steps(probes, ports),
    }
    return report


def _host() -> str:
    import platform

    return platform.platform()


def _next_steps(probes: list[dict[str, Any]], ports: list[dict[str, Any]]) -> list[str]:
    steps: list[str] = []
    if not any(p["id"] == "stlink" and p["toolInstalled"] for p in probes):
        steps.append("Install st-info (stlink tools) to probe ST-Link adapters")
    if not any(p["id"] == "stlink" and p["presence"] == "connected" for p in probes):
        steps.append("Connect an ST-Link to enable SWD flash/debug")
    if not ports:
        steps.append("No serial ports found — connect the board's USB-UART bridge")
    steps.append("Run identify_target() (OpenOCD) to confirm the MCU family via chip-id")
    return steps


REPORT_FILE = "discovery-report.json"


def save_report(report: dict[str, Any]) -> Path:
    path = Path(settings.workspace_root) / REPORT_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path


def load_report() -> dict[str, Any] | None:
    path = Path(settings.workspace_root) / REPORT_FILE
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
