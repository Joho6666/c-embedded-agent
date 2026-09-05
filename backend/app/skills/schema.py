from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VALID_CONTEXT_LEVELS = frozenset({"FOCUSED", "PROJECT", "DEEP"})
VALID_STATUSES = frozenset({"ready", "experimental", "unsupported", "not-supported", "draft", "deprecated"})


class SkillValidationError(ValueError):
    pass


def _strings(value: Any, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise SkillValidationError(f"{field_name} must be a list of strings")
    return tuple(value)


@dataclass(frozen=True)
class SkillDefinition:
    id: str
    name: str
    description: str
    platforms: tuple[str, ...]
    triggers: tuple[str, ...]
    exclusions: tuple[str, ...]
    capabilities: tuple[str, ...]
    required_tools: tuple[str, ...]
    required_context: tuple[str, ...]
    validators: tuple[Any, ...]
    golden_examples: tuple[Any, ...]
    known_errors: tuple[Any, ...]
    context_level: str
    enabled: bool
    status: str
    extra: dict[str, Any] = field(default_factory=dict, compare=False)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SkillDefinition":
        if not isinstance(raw, dict):
            raise SkillValidationError("skill must be an object")
        sid, name = raw.get("id"), raw.get("name")
        if not isinstance(sid, str) or not sid.strip():
            raise SkillValidationError("id must be a non-empty string")
        if not isinstance(name, str) or not name.strip():
            raise SkillValidationError(f"skill {sid}: name must be a non-empty string")
        status = raw.get("status", "ready")
        if status not in VALID_STATUSES:
            raise SkillValidationError(f"skill {sid}: invalid status {status!r}")
        level = str(raw.get("context_level", raw.get("contextLevel", "FOCUSED"))).upper()
        if level not in VALID_CONTEXT_LEVELS:
            raise SkillValidationError(f"skill {sid}: invalid context_level {level!r}")
        enabled = raw.get("enabled", True)
        if not isinstance(enabled, bool):
            raise SkillValidationError(f"skill {sid}: enabled must be boolean")
        platforms = raw.get("platforms")
        if platforms is None and isinstance(raw.get("platform"), str):
            platforms = [raw["platform"]]
        known = {
            "id", "name", "description", "platforms", "platform", "triggers", "exclusions",
            "capabilities", "required_tools", "requiredTools", "required_context", "requiredContext",
            "validators", "golden_examples", "goldenExamples", "known_errors", "knownErrors",
            "context_level", "contextLevel", "enabled", "status",
        }
        return cls(
            id=sid,
            name=name,
            description=str(raw.get("description", "")),
            platforms=_strings(platforms, "platforms"),
            triggers=_strings(raw.get("triggers", []), "triggers"),
            exclusions=_strings(raw.get("exclusions", []), "exclusions"),
            capabilities=_strings(raw.get("capabilities", []), "capabilities"),
            required_tools=_strings(raw.get("required_tools", raw.get("requiredTools", [])), "required_tools"),
            required_context=_strings(raw.get("required_context", raw.get("requiredContext", [])), "required_context"),
            validators=tuple(raw.get("validators") or []),
            golden_examples=tuple(raw.get("golden_examples", raw.get("goldenExamples")) or []),
            known_errors=tuple(raw.get("known_errors", raw.get("knownErrors")) or []),
            context_level=level,
            enabled=enabled,
            status=status,
            extra={key: value for key, value in raw.items() if key not in known},
        )

    def to_dict(self) -> dict[str, Any]:
        out = dict(self.extra)
        out.update({
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "platforms": list(self.platforms),
            "triggers": list(self.triggers),
            "exclusions": list(self.exclusions),
            "capabilities": list(self.capabilities),
            "required_tools": list(self.required_tools),
            "required_context": list(self.required_context),
            "validators": list(self.validators),
            "golden_examples": list(self.golden_examples),
            "known_errors": list(self.known_errors),
            "context_level": self.context_level,
            "enabled": self.enabled,
            "status": self.status,
        })
        # Old clients still consume these camelCase names.
        out["goldenExamples"] = list(self.golden_examples)
        out["knownErrors"] = list(self.known_errors)
        return out
