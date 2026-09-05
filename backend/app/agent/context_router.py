from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Iterable

from app.agent.task_classifier import ContextLevel


CONTEXT_BUDGETS = {
    ContextLevel.FOCUSED: 12_000,
    ContextLevel.PROJECT: 24_000,
    ContextLevel.DEEP: 48_000,
}
CONTEXT_SKILL_LIMITS = {
    ContextLevel.FOCUSED: 1,
    ContextLevel.PROJECT: 2,
    ContextLevel.DEEP: 4,
}
SOURCE_BUDGETS = {
    "platform_facts": 2_500,
    "errors": 4_000,
    "explicit_context": 6_000,
    "relevant_files": 16_000,
    "skills": 6_000,
    "knowledge": 6_000,
    "project_tree": 4_000,
    "history": 8_000,
}
SOURCE_PRIORITIES = {
    "platform_facts": 1,
    "errors": 2,
    "relevant_files": 3,
    "skills": 4,
    "explicit_context": 5,
    "knowledge": 6,
    "project_tree": 7,
    "history": 8,
}


def _infer_fact_origin(key: str) -> str:
    if key in {"adapterId", "platform", "framework"}:
        return "platform_detection"
    if key in {"mcu", "core", "clockMHz", "flashKb", "ramKb", "flash_kb", "ram_kb"}:
        return "mcu_profile"
    if key in {"board", "led"}:
        return "board_profile"
    if key == "ioc":
        return "ioc_analysis"
    if key == "sdkconfig":
        return "sdkconfig"
    if key in {"Makefile", "CMakeLists"}:
        return "build_definition"
    return "project.json"


@dataclass(frozen=True)
class RoutedContext:
    context: dict[str, Any]
    level: ContextLevel
    budget: int
    used_chars: int
    included_sources: tuple[str, ...]
    truncated_sources: tuple[str, ...]
    reasons: tuple[str, ...]
    evidence_origins: dict[str, str] = field(default_factory=dict)
    source_telemetry: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.context,
            "_routing": {
                "contextLevel": self.level.value,
                "budget": self.budget,
                "usedChars": self.used_chars,
                "approxTokens": self.used_chars // 4,
                "includedSources": list(self.included_sources),
                "truncatedSources": list(self.truncated_sources),
                "reasons": list(self.reasons),
                "evidenceOrigins": dict(self.evidence_origins),
                "sourceTelemetry": list(self.source_telemetry),
            },
        }


def _size(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


class ContextRouter:
    """Builds a deterministic, audited context within a character budget."""

    def route(
        self,
        context: dict[str, Any] | None = None,
        *,
        level: ContextLevel | str = ContextLevel.PROJECT,
        platform_facts: dict[str, Any] | None = None,
        errors: Iterable[Any] | None = None,
        explicit_context: Iterable[Any] | dict[str, Any] | None = None,
        relevant_files: Iterable[Any] | None = None,
        skills: Iterable[Any] | None = None,
        knowledge: Iterable[Any] | None = None,
        project_tree: Iterable[Any] | None = None,
        skill_overflow_reason: str | None = None,
    ) -> RoutedContext:
        selected_level = level if isinstance(level, ContextLevel) else ContextLevel(str(level).upper())
        budget = CONTEXT_BUDGETS[selected_level]
        source = context or {}
        facts = platform_facts or {
            key: source.get(key)
            for key in ("adapterId", "platform", "mcu", "core", "flash_kb", "ram_kb", "framework", "compiler", "board", "led", "ioc", "project", "priority")
            if source.get(key) is not None
        }
        candidates: list[tuple[str, Any, bool]] = [
            ("platform_facts", facts, True),
            ("errors", list(errors if errors is not None else source.get("errors") or []), False),
            ("explicit_context", explicit_context if explicit_context is not None else source.get("explicit_context") or [], False),
            ("relevant_files", list(relevant_files if relevant_files is not None else source.get("relevant_files") or []), False),
        ]
        skill_items = list(skills if skills is not None else source.get("skills") or [])
        skill_limit = CONTEXT_SKILL_LIMITS[selected_level]
        reasons: list[str] = []
        if len(skill_items) > skill_limit:
            if skill_overflow_reason:
                reasons.append("skill-overflow:" + skill_overflow_reason)
            else:
                skill_items = skill_items[:skill_limit]
                reasons.append(f"skills-limited:{skill_limit}")
        candidates += [
            ("skills", skill_items, False),
            ("knowledge", list(knowledge if knowledge is not None else source.get("knowledge") or []), False),
            ("project_tree", list(project_tree if project_tree is not None else source.get("project_tree") or []), False),
        ]

        routed: dict[str, Any] = {}
        included: list[str] = []
        truncated: list[str] = []
        for name, value, mandatory in candidates:
            if value in (None, [], {}):
                routed[name] = value
                continue
            tentative = {**routed, name: value}
            if _size(tentative) <= budget or mandatory:
                routed[name] = value
                included.append(name)
                continue
            if isinstance(value, list):
                kept: list[Any] = []
                for item in value:
                    if _size({**routed, name: kept + [item]}) > budget:
                        break
                    kept.append(item)
                routed[name] = kept
                if kept:
                    included.append(name)
            else:
                routed[name] = []
            truncated.append(name)

        # Retain non-budgeted scalar lifecycle facts used by the existing runtime.
        for key in ("iteration",):
            if key in source:
                routed[key] = source[key]
        used = _size(routed)
        evidence_origins = {k: _infer_fact_origin(k) for k in facts}

        source_telemetry: list[dict[str, Any]] = []
        for name, value, mandatory in candidates:
            val_chars = _size(routed.get(name)) if routed.get(name) not in (None, [], {}) else 0
            source_telemetry.append({
                "source": name,
                "priority": SOURCE_PRIORITIES.get(name, 9),
                "allocatedBudget": SOURCE_BUDGETS.get(name, 5000),
                "chars": val_chars,
                "approxTokens": val_chars // 4,
                "truncated": name in truncated,
            })

        return RoutedContext(
            routed,
            selected_level,
            budget,
            used,
            tuple(included),
            tuple(truncated),
            tuple(reasons),
            evidence_origins=evidence_origins,
            source_telemetry=source_telemetry,
        )


def route_context(context: dict[str, Any], *, level: ContextLevel | str = ContextLevel.PROJECT) -> dict[str, Any]:
    return ContextRouter().route(context, level=level).to_dict()


def replace_current_context(messages: list[dict[str, Any]], content: str) -> list[dict[str, Any]]:
    """Replace the prior routed-context message instead of growing each LLM round."""

    marker = "[CURRENT_CONTEXT]\n"
    kept = [message for message in messages if not (message.get("role") == "system" and str(message.get("content", "")).startswith(marker))]
    return [*kept, {"role": "system", "content": marker + content}]
