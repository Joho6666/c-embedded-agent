from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.platforms.base import DetectionEvidence, PlatformAdapter


@dataclass(frozen=True)
class Resolution:
    status: str
    adapter: PlatformAdapter | None = None
    reason: str | None = None
    evidence: tuple[DetectionEvidence, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "adapterId": self.adapter.adapter_id if self.adapter else None,
            "reason": self.reason,
            "evidence": [item.to_dict() for item in self.evidence],
        }


class PlatformRegistry:
    def __init__(self, adapters: list[PlatformAdapter] | None = None) -> None:
        self._adapters: dict[str, PlatformAdapter] = {}
        self._aliases: dict[str, str] = {}
        for adapter in adapters or []:
            self.register(adapter)

    def register(self, adapter: PlatformAdapter, *, aliases: tuple[str, ...] = ()) -> None:
        adapter_id = adapter.adapter_id.lower()
        if adapter_id in self._adapters:
            raise ValueError(f"duplicate platform adapter: {adapter.adapter_id}")
        self._adapters[adapter_id] = adapter
        values = {
            adapter.adapter_id,
            adapter.descriptor.platform,
            adapter.descriptor.mcu,
            f"{adapter.descriptor.platform}:{adapter.descriptor.framework}",
            *aliases,
        }
        for value in values:
            key = self._normalize(value)
            existing = self._aliases.get(key)
            if existing and existing != adapter_id:
                continue
            self._aliases[key] = adapter_id

    def get(self, adapter_id: str) -> PlatformAdapter | None:
        key = self._aliases.get(self._normalize(adapter_id), self._normalize(adapter_id))
        return self._adapters.get(key)

    def list_platforms(self) -> list[dict[str, Any]]:
        return [self._adapters[key].descriptor.to_dict() for key in sorted(self._adapters)]

    def resolve_explicit(
        self,
        *,
        adapter_id: str | None = None,
        platform: str | None = None,
        mcu: str | None = None,
        framework: str | None = None,
    ) -> Resolution:
        supplied = [("adapterId", adapter_id), ("platform", platform), ("mcu", mcu)]
        resolved: list[tuple[str, PlatformAdapter]] = []
        for label, value in supplied:
            if not value:
                continue
            adapter = self.get(value)
            if adapter is None:
                return Resolution("unsupported", reason=f"unsupported {label}: {value}")
            resolved.append((label, adapter))
        unique = {adapter.adapter_id for _, adapter in resolved}
        if len(unique) > 1:
            detail = ", ".join(f"{label}={adapter.adapter_id}" for label, adapter in resolved)
            return Resolution("ambiguous", reason=f"conflicting explicit platform selection: {detail}")
        if not resolved:
            return Resolution("unsupported", reason="platform, mcu, or adapterId is required")
        adapter = resolved[0][1]
        if framework and self._normalize(framework) != self._normalize(adapter.descriptor.framework):
            return Resolution("unsupported", reason=f"unsupported framework for {adapter.adapter_id}: {framework}")
        return Resolution("resolved", adapter=adapter)

    def detect(self, root: Path) -> Resolution:
        root = Path(root)
        if not root.is_dir():
            return Resolution("unsupported", reason=f"project directory does not exist: {root}")
        evidence = tuple(adapter.detect_project(root) for adapter in self._adapters.values())
        matches = [item for item in evidence if item.matched]
        if len(matches) > 1:
            names = ", ".join(item.adapter_id for item in matches)
            return Resolution("ambiguous", reason=f"project matches multiple adapters: {names}", evidence=evidence)
        if not matches:
            conflicts = sorted({c for item in evidence for c in item.conflicts})
            reason = "; ".join(conflicts) if conflicts else "no registered platform matched the project"
            return Resolution("unsupported", reason=reason, evidence=evidence)
        return Resolution("resolved", adapter=self.get(matches[0].adapter_id), evidence=evidence)

    def resolve_project(
        self,
        root: Path,
        *,
        adapter_id: str | None = None,
        platform: str | None = None,
        mcu: str | None = None,
        framework: str | None = None,
    ) -> Resolution:
        explicit_values = (adapter_id, platform, mcu, framework)
        detected = self.detect(root)
        if not any(explicit_values):
            return detected
        explicit = self.resolve_explicit(
            adapter_id=adapter_id,
            platform=platform,
            mcu=mcu,
            framework=framework,
        )
        if explicit.status != "resolved":
            return explicit
        if detected.status == "resolved" and detected.adapter and detected.adapter.adapter_id != explicit.adapter.adapter_id:
            return Resolution(
                "ambiguous",
                reason=(
                    f"explicit adapter {explicit.adapter.adapter_id} conflicts with detected "
                    f"adapter {detected.adapter.adapter_id}"
                ),
                evidence=detected.evidence,
            )
        if detected.status == "ambiguous":
            return detected
        return Resolution("resolved", adapter=explicit.adapter, evidence=detected.evidence)

    @staticmethod
    def _normalize(value: str) -> str:
        return "".join(ch for ch in value.strip().lower() if ch.isalnum())


def default_registry(repo_root: Path) -> PlatformRegistry:
    from app.platforms.esp32s3.adapter import Esp32S3IdfAdapter
    from app.platforms.stm32f103.adapter import Stm32F103Adapter

    root = Path(repo_root)
    registry = PlatformRegistry()
    registry.register(
        Stm32F103Adapter(root),
        aliases=("stm32", "stm32f1", "stm32f103", "stm32f103c8", "stm32f103c8tx", "blue-pill", "hal"),
    )
    registry.register(
        Esp32S3IdfAdapter(root),
        aliases=("esp32s3", "esp32-s3", "esp-idf", "devkitc-1"),
    )
    return registry


__all__ = ["PlatformRegistry", "Resolution", "default_registry"]
