"""hardware-map.yaml — Zephyr-Twister-inspired hardware inventory.

Deliberately a small, explicit subset parser (no PyYAML dependency):

    defaults:
      baud: 115200
    devices:
      - id: bluepill-01
        platform: stm32
        board: Blue Pill
        mcu: STM32F103C8T6
        probe: ST-Link
        probeSerial: "0668FF..."
        serial: COM7
        baud: 115200
        capabilities: [flash, serial, gpio-probe]
        tags: [golden, lab-a]

Tasks may declare `requiredDevices: 2`; `check_required_devices` reports
whether the map can satisfy that — without pretending devices exist.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config.settings import settings


class HardwareMapError(ValueError):
    pass


def _parse_scalar(text: str) -> Any:
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(x) for x in inner.split(",")]
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    if text in ("null", "~", ""):
        return None
    if text in ("true", "false"):
        return text == "true"
    try:
        return int(text)
    except ValueError:
        return text


def parse_hardware_map(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {"defaults": {}, "devices": []}
    current: dict[str, Any] | None = None
    section: str | None = None

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.strip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        if indent == 0 and line.endswith(":") and not line.startswith("- "):
            section = line[:-1].strip()
            if section == "devices":
                result["devices"] = []
                current = None
            elif section == "defaults":
                result.setdefault("defaults", {})
            else:
                section = None
            continue

        if section == "devices" and line.startswith("- "):
            current = {}
            result["devices"].append(current)
            line = line[2:].strip()

        if section == "defaults" and indent > 0 and ":" in line:
            key, _, value = line.partition(":")
            result["defaults"][key.strip()] = _parse_scalar(value)
            continue

        if current is not None and ":" in line:
            key, _, value = line.partition(":")
            current[key.strip()] = _parse_scalar(value)
            continue

        if current is None and section is None and ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = _parse_scalar(value)

    return result


def load_hardware_map(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path) if path else Path(settings.workspace_root) / "hardware-map.yaml"
    if not p.is_file():
        return {"defaults": {}, "devices": [], "source": None, "available": False}
    parsed = parse_hardware_map(p.read_text(encoding="utf-8"))
    parsed["source"] = str(p)
    parsed["available"] = True
    return parsed


def online_devices(map_data: dict[str, Any], registry: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Devices from the map that the registry currently shows ONLINE."""
    registry = registry or []
    status_by_id = {d.get("id"): d.get("status") for d in registry}
    out = []
    for d in map_data.get("devices") or []:
        did = str(d.get("id") or "")
        out.append({**d, "status": status_by_id.get(did, "UNKNOWN")})
    return out


def check_required_devices(
    required: int | None,
    map_data: dict[str, Any],
    registry: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    devices = [d for d in online_devices(map_data, registry) if d.get("status") == "ONLINE"]
    if required is None:
        required = 0
    return {
        "required": required,
        "configured": len(map_data.get("devices") or []),
        "online": [d.get("id") for d in devices],
        "satisfied": len(devices) >= required,
        "missing": max(0, required - len(devices)),
    }
