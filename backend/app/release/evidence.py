from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class CapabilityStatus(StrEnum):
    IMPLEMENTED = "IMPLEMENTED"
    VERIFIED_LOCAL = "VERIFIED_LOCAL"
    VERIFIED_CI = "VERIFIED_CI"
    VERIFIED_HARDWARE = "VERIFIED_HARDWARE"
    EXPERIMENTAL = "EXPERIMENTAL"
    UNAVAILABLE = "UNAVAILABLE"
    FAIL = "FAIL"
    NOT_TESTED = "NOT_TESTED"


@dataclass(frozen=True)
class CapabilityEvidence:
    capability: str
    implemented: bool
    verified_ci: bool = False
    verified_hardware: bool = False
    status: CapabilityStatus = CapabilityStatus.IMPLEMENTED
    evidence: tuple[str, ...] = ()
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability,
            "implemented": self.implemented,
            "verified_ci": self.verified_ci,
            "verified_hardware": self.verified_hardware,
            "status": self.status.value,
            "evidence": list(self.evidence),
            "reason": self.reason,
        }


@dataclass
class PlatformCapabilityAudit:
    adapter_id: str
    platform: str
    mcu: str
    framework: str
    status: str  # ready, experimental, planned
    capabilities: dict[str, CapabilityEvidence] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapterId": self.adapter_id,
            "platform": self.platform,
            "mcu": self.mcu,
            "framework": self.framework,
            "status": self.status,
            "capabilities": {k: v.to_dict() for k, v in self.capabilities.items()},
        }
