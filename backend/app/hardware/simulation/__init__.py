"""Simulation adapters registry."""

from __future__ import annotations

from typing import Any

from app.hardware.simulation.base import SimulationAdapter
from app.hardware.simulation.renode import RenodeAdapter

_REGISTRY: dict[str, type[SimulationAdapter]] = {
    "renode": RenodeAdapter,
}


def get_adapter(adapter_id: str = "renode") -> SimulationAdapter:
    cls = _REGISTRY.get(str(adapter_id or "").lower())
    if cls is None:
        raise KeyError(f"unknown simulation adapter: {adapter_id!r}")
    return cls()


def list_adapters() -> list[dict[str, Any]]:
    out = []
    for sid, cls in _REGISTRY.items():
        detect = cls().detect()
        out.append(
            {
                "id": sid,
                "label": cls.label,
                "adapterStatus": detect.get("adapterStatus", cls.adapter_status),
                "available": bool(detect.get("available")),
                "version": detect.get("version"),
            }
        )
    return out
