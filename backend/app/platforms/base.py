from __future__ import annotations

import asyncio
import shutil
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

LineCallback = Callable[[str, str], Awaitable[None] | None]
PlatformStatus = Literal["ready", "experimental", "unsupported"]
OperationStatus = Literal["PASS", "FAIL", "UNAVAILABLE", "SKIPPED"]


@dataclass(frozen=True)
class PlatformDescriptor:
    adapter_id: str
    name: str
    platform: str
    mcu: str
    framework: str
    status: PlatformStatus
    boards: tuple[str, ...] = ()
    toolchains: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["adapterId"] = data.pop("adapter_id")
        data["id"] = data["adapterId"]
        data["mcus"] = [data["mcu"]]
        data["frameworks"] = [data["framework"]]
        data["boards"] = list(self.boards)
        data["toolchains"] = list(self.toolchains)
        data["capabilities"] = list(self.capabilities)
        return data


@dataclass(frozen=True)
class DetectionEvidence:
    adapter_id: str
    matched: bool
    confidence: float
    reasons: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["adapterId"] = data.pop("adapter_id")
        data["reasons"] = list(self.reasons)
        data["conflicts"] = list(self.conflicts)
        return data


@dataclass
class PlatformResult:
    status: OperationStatus
    operation: str
    adapter_id: str
    data: dict[str, Any] = field(default_factory=dict)
    reason: str | None = None
    evidence: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.status == "PASS"

    def to_dict(self) -> dict[str, Any]:
        output = {
            "success": self.success,
            "status": self.status,
            "operation": self.operation,
            "adapterId": self.adapter_id,
            "reason": self.reason,
            "evidence": list(self.evidence),
        }
        output.update({key: value for key, value in self.data.items() if key != "success"})
        return output

    @classmethod
    def unavailable(cls, operation: str, adapter_id: str, reason: str) -> PlatformResult:
        return cls(status="UNAVAILABLE", operation=operation, adapter_id=adapter_id, reason=reason)


class PlatformAdapter(ABC):
    """Stable platform boundary used by runtime, API, and project management.

    Device-facing defaults deliberately return UNAVAILABLE. An adapter must never
    infer successful hardware execution from static files or a missing probe.
    """

    descriptor: PlatformDescriptor

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root).resolve()

    @property
    def adapter_id(self) -> str:
        return self.descriptor.adapter_id

    @property
    @abstractmethod
    def template_path(self) -> Path:
        raise NotImplementedError

    @property
    def protected_paths(self) -> tuple[str, ...]:
        return (".git", "project.json")

    @property
    def tools(self) -> tuple[str, ...]:
        return ()

    @property
    def skills(self) -> tuple[str, ...]:
        return ()

    @property
    def validators(self) -> tuple[str, ...]:
        return ()

    @property
    def knowledge_roots(self) -> tuple[Path, ...]:
        return ()

    @abstractmethod
    def detect_project(self, root: Path) -> DetectionEvidence:
        raise NotImplementedError

    @abstractmethod
    def create_template(
        self,
        destination: Path,
        *,
        name: str,
        board: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> PlatformResult:
        raise NotImplementedError

    @abstractmethod
    def load_context(self, root: Path) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def toolchain_status(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def build(self, root: Path) -> PlatformResult:
        raise NotImplementedError

    async def build_streaming(self, root: Path, on_line: LineCallback | None = None) -> PlatformResult:
        return await asyncio.to_thread(self.build, root)

    def clean(self, root: Path) -> PlatformResult:
        return PlatformResult.unavailable("clean", self.adapter_id, "clean is not implemented for this adapter")

    def flash(self, root: Path, *, device: str | None = None) -> PlatformResult:
        return PlatformResult.unavailable("flash", self.adapter_id, "hardware flash is unavailable")

    def reset(self, *, device: str | None = None) -> PlatformResult:
        return PlatformResult.unavailable("reset", self.adapter_id, "hardware reset is unavailable")

    def serial_sample(
        self,
        *,
        device: str | None,
        baud: int = 115200,
        seconds: float = 8.0,
        expect: str | None = None,
    ) -> PlatformResult:
        return PlatformResult.unavailable("serial", self.adapter_id, "serial device is unavailable")

    def generate_peripheral(self, root: Path, kind: str, args: Mapping[str, Any] | None = None) -> PlatformResult:
        return PlatformResult.unavailable("generate", self.adapter_id, f"unsupported peripheral: {kind}")

    def validate_static(self, root: Path, task: str = "") -> PlatformResult:
        return PlatformResult.unavailable("validate", self.adapter_id, "static validation is unavailable")

    def validate_hardware(
        self,
        *,
        serial_lines: list[str] | None,
        expect: str | None,
        task: str,
        has_probe: bool,
    ) -> PlatformResult:
        return PlatformResult.unavailable("hardware-validation", self.adapter_id, "Hardware Not Tested")

    def hardware_run(
        self,
        root: Path,
        *,
        serial_device: str | None = None,
        baud: int = 115200,
        expect: str | None = None,
        task: str = "",
        max_hw_iterations: int = 3,
    ) -> PlatformResult:
        return PlatformResult.unavailable("hardware-run", self.adapter_id, "hardware runner is unavailable")

    @staticmethod
    def copy_template(source: Path, destination: Path) -> None:
        if destination.exists():
            raise FileExistsError(destination)
        shutil.copytree(
            source,
            destination,
            ignore=shutil.ignore_patterns("*.elf", "*.hex", "*.bin", "*.o", "*.map", ".git", "build"),
        )


__all__ = [
    "DetectionEvidence",
    "LineCallback",
    "OperationStatus",
    "PlatformAdapter",
    "PlatformDescriptor",
    "PlatformResult",
    "PlatformStatus",
]
