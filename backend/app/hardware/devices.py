"""Persistent HardwareDevice registry (workspace-level).

Store: `<workspace_root>/hardware-devices.json`. Discovery refresh adopts
candidates, marks seen/absent devices, and never invents capabilities.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config.settings import settings
from app.hardware.models import DeviceError, mark_absent, mark_seen, normalize_device


def store_path() -> Path:
    return Path(settings.workspace_root) / "hardware-devices.json"


def load_devices() -> list[dict[str, Any]]:
    path = store_path()
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    out = []
    for item in raw if isinstance(raw, list) else []:
        try:
            out.append(normalize_device(item))
        except DeviceError:
            continue
    return out


def save_devices(devices: list[dict[str, Any]]) -> Path:
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(devices, indent=2), encoding="utf-8")
    return path


def upsert_device(raw: dict[str, Any]) -> dict[str, Any]:
    device = normalize_device(raw)
    devices = load_devices()
    for i, existing in enumerate(devices):
        if existing["id"] == device["id"]:
            device.setdefault("source", existing.get("source") or "manual")
            device["lastSeenAt"] = device.get("lastSeenAt") or existing.get("lastSeenAt")
            device["lastVerifiedAt"] = device.get("lastVerifiedAt") or existing.get("lastVerifiedAt")
            devices[i] = device
            break
    else:
        devices.append(device)
    save_devices(devices)
    return device


def delete_device(device_id: str) -> bool:
    devices = load_devices()
    kept = [d for d in devices if d["id"] != device_id]
    if len(kept) == len(devices):
        return False
    save_devices(kept)
    return True


def refresh_from_discovery(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Adopt discovery candidates and update seen/absent state."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    discovered = {d["id"]: d for d in report.get("devices") or []}
    devices = load_devices()

    by_id = {d["id"]: d for d in devices}
    for did, candidate in discovered.items():
        if did in by_id:
            existing = by_id[did]
            existing["debugProbe"] = existing.get("debugProbe") or candidate.get("debugProbe")
            existing["serialPort"] = existing.get("serialPort") or candidate.get("serialPort")
            existing["platformHint"] = existing.get("platformHint") or candidate.get("platformHint")
            existing["capabilities"] = sorted(
                set(existing.get("capabilities") or []) | set(candidate.get("capabilities") or [])
            )
            mark_seen(existing, now)
        else:
            by_id[did] = candidate
            mark_seen(candidate, now)

    for d in by_id.values():
        if d["id"] not in discovered and d.get("source") == "discovery":
            mark_absent(d, now)

    out = list(by_id.values())
    save_devices(out)
    return out
