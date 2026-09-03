from __future__ import annotations

from typing import Any

from app.agent.task_classifier import ContextLevel, TaskClassifier
from app.agent.workflow_router import WorkflowRouter


def make_plan(prompt: str) -> list[dict[str, Any]]:
    steps = list(WorkflowRouter().route(prompt).steps)
    return [{"id": f"s{i+1}", "index": i + 1, "title": t, "status": "pending"} for i, t in enumerate(steps)]


def looks_complex(prompt: str) -> bool:
    return TaskClassifier().classify(prompt).context_level is not ContextLevel.FOCUSED
