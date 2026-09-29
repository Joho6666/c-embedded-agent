"""HardwareDevice data model.

A device describes what is *proven* about a physical unit. `mcu` stays
"UNKNOWN" until SWD chip-id evidence exists; `capabilities` only lists what
the runtime actually exercised (e.g. "usb-serial", "debug-probe", "flash").
"""

from __future__ import annotations

from typing import Any

DEVICE_STATUS = ("ONLINE", "OFFLINE", "BUSY", "UNKNOWN", "FAULT")
MCU_EVIDENCE = (None, "manual", "usb-hint", "swd-chip-id-family", "swd-chip-id-exact")

DEFAULT_DEVICE: dict[str, Any] = {
    "id": "",
    "platformId": "unknown",
    "platformHint": None,
    "board": "UNKNOWN",
    "mcu": "UNKNOWN",
    "mcuEvidence": None,
    "serialNumber": None,
    "debugProbe": None,
    "debugProbeSerial": None,
    "serialPort": None,
    "baud": 115200,
    "flashRunner": None,
    "powerController": None,
    "measurementCapabilities": [],  # gpioProbe / logicAnalyzer / oscilloscope / multimeter
    "capabilities": [],  # only what has actually been exercised
    "status": "UNKNOWN",
    "lastSeenAt": None,
    "lastVerifiedAt": None,
    "source": "manual",  # manual | discovery
}


class DeviceError(ValueError):
    pass


def normalize_device(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw, dict) or not str(raw.get("id") or "").strip():
        raise DeviceError("device requires a non-empty id")
    out = dict(DEFAULT_DEVICE)
    for key, default in DEFAULT_DEVICE.items():
        value = raw.get(key, default)
        if key in ("measurementCapabilities", "capabilities") and value is None:
            value = []
        out[key] = value
    if out["status"] not in DEVICE_STATUS:
        raise DeviceError(f"invalid device status: {out['status']!r}")
    if out["mcuEvidence"] not in MCU_EVIDENCE:
        raise DeviceError(f"invalid mcuEvidence: {out['mcuEvidence']!r}")
    # Honesty gate: a concrete MCU claim must cite evidence beyond a USB hint.
    if out["mcu"] not in ("UNKNOWN", "", None) and out["mcuEvidence"] not in (
        "swd-chip-id-family",
        "swd-chip-id-exact",
        "manual",
    ):
        raise DeviceError("mcu claim requires swd-chip-id or manual evidence, not a USB hint")
    for key in ("measurementCapabilities", "capabilities"):
        if not isinstance(out[key], list):
            raise DeviceError(f"{key} must be a list")
    if not isinstance(out["baud"], int):
        out["baud"] = 115200
    return out


def mark_seen(device: dict[str, Any], when: str) -> dict[str, Any]:
    device["lastSeenAt"] = when
    if device["status"] in ("OFFLINE", "UNKNOWN"):
        device["status"] = "ONLINE"
    return device


def mark_absent(device: dict[str, Any], when: str) -> dict[str, Any]:
    if device["status"] != "BUSY":
        device["status"] = "OFFLINE"
        device["lastSeenAt"] = device.get("lastSeenAt") or when
    return device
