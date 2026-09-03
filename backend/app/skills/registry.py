from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from app.skills.schema import SkillDefinition, SkillValidationError


class DuplicateSkillError(SkillValidationError):
    pass


class SkillRegistry:
    def __init__(self, roots: Iterable[Path] | None = None) -> None:
        base = Path(__file__).resolve().parent
        self.roots = tuple(roots or (base,))
        self._skills: dict[str, SkillDefinition] = {}
        self.reload()

    def reload(self) -> None:
        loaded: dict[str, SkillDefinition] = {}
        for root in self.roots:
            if not root.exists():
                continue
            paths = sorted(path for path in root.glob("*/*.json") if path.is_file())
            # Compatibility with the pre-v0.9 aggregate catalog when no split files exist.
            if not paths:
                paths = sorted(path for path in root.glob("*.json") if path.is_file())
            for path in paths:
                raw = json.loads(path.read_text(encoding="utf-8"))
                records = raw if isinstance(raw, list) else [raw]
                for record in records:
                    skill = SkillDefinition.from_dict(record)
                    if skill.id in loaded:
                        raise DuplicateSkillError(f"duplicate skill id {skill.id!r} in {path}")
                    loaded[skill.id] = skill
        self._skills = loaded

    def get(self, skill_id: str, *, include_disabled: bool = True) -> SkillDefinition | None:
        skill = self._skills.get(skill_id)
        if skill and (include_disabled or skill.enabled):
            return skill
        return None

    def list(self, *, platform: str | None = None, include_disabled: bool = True) -> list[SkillDefinition]:
        skills = self._skills.values()
        if not include_disabled:
            skills = (skill for skill in skills if skill.enabled and skill.status not in {"unsupported", "not-supported", "deprecated"})
        if platform:
            wanted = platform.casefold()
            skills = (skill for skill in skills if any(item.casefold() == wanted for item in skill.platforms))
        return sorted(skills, key=lambda skill: skill.id)


_default_registry: SkillRegistry | None = None


def default_skill_registry() -> SkillRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = SkillRegistry()
    return _default_registry
