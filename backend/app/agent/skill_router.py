from __future__ import annotations

from dataclasses import dataclass

from app.agent.task_classifier import ContextLevel
from app.skills.registry import SkillRegistry, default_skill_registry
from app.skills.schema import SkillDefinition


SKILL_LIMITS = {ContextLevel.FOCUSED: 1, ContextLevel.PROJECT: 2, ContextLevel.DEEP: 4}


@dataclass(frozen=True)
class SkillSelection:
    skills: tuple[SkillDefinition, ...]
    context_level: ContextLevel
    limit: int
    reasons: tuple[str, ...]


class SkillRouter:
    def __init__(self, registry: SkillRegistry | None = None) -> None:
        self.registry = registry or default_skill_registry()

    def select(
        self,
        prompt: str,
        *,
        platform: str | None = None,
        context_level: ContextLevel | str = ContextLevel.FOCUSED,
        limit: int | None = None,
        allow_overflow_reason: str | None = None,
    ) -> SkillSelection:
        level = context_level if isinstance(context_level, ContextLevel) else ContextLevel(str(context_level).upper())
        normal_limit = SKILL_LIMITS[level]
        selected_limit = normal_limit if limit is None else limit
        if selected_limit > normal_limit and not allow_overflow_reason:
            raise ValueError("selecting more skills than the context level allows requires a reason")
        text = prompt.casefold()
        candidates: list[tuple[int, int, str, SkillDefinition]] = []
        for skill in self.registry.list(include_disabled=False):
            if platform and skill.platforms and platform.casefold() not in {p.casefold() for p in skill.platforms}:
                continue
            triggers = skill.triggers or (skill.id.replace("-", " "), skill.id)
            if any(exclusion.casefold() in text for exclusion in skill.exclusions):
                continue
            matched = [trigger for trigger in triggers if trigger.casefold() in text]
            if not matched:
                continue
            # More matched words and longer compound triggers are more specific.
            specificity = max(len(trigger.split()) for trigger in matched)
            candidates.append((specificity, len(matched), skill.id, skill))
        candidates.sort(key=lambda row: (-row[0], -row[1], row[2]))

        chosen: list[SkillDefinition] = []
        for _, _, _, skill in candidates:
            if any(existing.id in skill.id.split("-") or skill.id in existing.id.split("-") for existing in chosen):
                continue
            chosen.append(skill)
            if len(chosen) >= selected_limit:
                break
        reasons = [f"matched:{skill.id}" for skill in chosen]
        if allow_overflow_reason and selected_limit > normal_limit:
            reasons.append("overflow:" + allow_overflow_reason)
        return SkillSelection(tuple(chosen), level, selected_limit, tuple(reasons))
