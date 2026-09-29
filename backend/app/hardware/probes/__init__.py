"""Registered probe adapters.

SUPPORTED requires a real test against the hardware lab. pyOCD and J-Link
adapters are declared but NOT_SUPPORTED: they refuse hardware actions with an
honest reason until someone runs them against real boards and upgrades them.
"""

from __future__ import annotations

import shutil
from typing import Any

from app.hardware.probes.base import DebugProbeAdapter
from app.hardware.probes.openocd import OpenOCDAdapter


class _UntestedAdapter(DebugProbeAdapter):
    tool_names: tuple[str, ...] = ()

    def detect(self) -> dict[str, Any]:
        installed = any(shutil.which(t) for t in self.tool_names) if self.tool_names else False
        return {
            "available": False,
            "adapterStatus": self.adapter_status,
            "toolInstalled": installed,
            "probeConnected": False,
            "status": "UNAVAILABLE",
            "reason": self.untested_reason(),
        }

    def untested_reason(self) -> str:
        return f"{self.label} adapter is declared but NOT_SUPPORTED — it has never been tested on the CEA hardware lab"

    def identify_target(self) -> dict[str, Any]:
        return {"available": False, "status": "UNAVAILABLE", "reason": self.untested_reason()}

    def flash(self, elf_path: str) -> dict[str, Any]:
        return {"available": False, "status": "UNAVAILABLE", "success": False, "reason": self.untested_reason()}

    def reset(self, mode: str = "run") -> dict[str, Any]:
        return {"available": False, "status": "UNAVAILABLE", "reason": self.untested_reason()}

    def halt(self) -> dict[str, Any]:
        return {"available": False, "status": "UNAVAILABLE", "reason": self.untested_reason()}

    def resume(self) -> dict[str, Any]:
        return {"available": False, "status": "UNAVAILABLE", "reason": self.untested_reason()}

    def read_register(self, name: str) -> dict[str, Any]:
        return {"available": False, "status": "UNAVAILABLE", "reason": self.untested_reason()}

    def read_memory32(self, name: str) -> dict[str, Any]:
        return {"available": False, "status": "UNAVAILABLE", "reason": self.untested_reason()}


class PyOCDAdapter(_UntestedAdapter):
    id = "pyocd"
    label = "pyOCD"
    adapter_status = "NOT_SUPPORTED"
    tool_names = ("pyocd",)


class JLinkAdapter(_UntestedAdapter):
    id = "jlink"
    label = "SEGGER J-Link"
    adapter_status = "NOT_SUPPORTED"
    tool_names = ("JLink.exe", "JLinkExe")


_REGISTRY: dict[str, type[DebugProbeAdapter]] = {
    "openocd": OpenOCDAdapter,
    "pyocd": PyOCDAdapter,
    "jlink": JLinkAdapter,
}


def get_probe(adapter_id: str = "openocd") -> DebugProbeAdapter:
    cls = _REGISTRY.get(str(adapter_id or "").lower())
    if cls is None:
        raise KeyError(f"unknown probe adapter: {adapter_id!r}")
    return cls()


def list_probes() -> list[dict[str, Any]]:
    out = []
    for pid, cls in _REGISTRY.items():
        adapter = cls()
        detect = adapter.detect()
        out.append(
            {
                "id": pid,
                "label": adapter.label,
                "adapterStatus": detect.get("adapterStatus", adapter.adapter_status),
                "toolInstalled": bool(detect.get("toolInstalled")),
                "probeConnected": bool(detect.get("probeConnected")),
                "reason": detect.get("reason"),
            }
        )
    return out
