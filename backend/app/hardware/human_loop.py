"""Human-in-the-loop — WAITING_FOR_USER for physical actions.

When a validation step needs a human (press a button, move a jumper, adjust
the potentiometer, confirm an LED), the agent must pause, state exactly what
to do, and wait. The action is recorded only after explicit confirmation —
the runtime never pretends a physical action happened.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config.settings import settings


def _store_path() -> Path:
    return Path(settings.workspace_root) / "user-actions.json"


def request_user_action(action: str, *, project_id: str | None = None, detail: str | None = None) -> dict[str, Any]:
    if not str(action or "").strip():
        raise ValueError("action description required")
    req = {
        "id": f"ua-{uuid.uuid4().hex[:10]}",
        "action": action,
        "projectId": project_id,
        "detail": detail,
        "status": "WAITING_FOR_USER",
        "requestedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "resolvedAt": None,
        "result": None,
    }
    _append(req)
    return req


def confirm_user_action(action_id: str, result: str = "confirmed") -> dict[str, Any]:
    """Record that the human actually performed the physical action."""
    items = _load()
    for req in items:
        if req.get("id") == action_id and req.get("status") == "WAITING_FOR_USER":
            req["status"] = "CONFIRMED" if result == "confirmed" else "DECLINED"
            req["result"] = result
            req["resolvedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            _save(items)
            return req
    raise ValueError(f"waiting action not found or already resolved: {action_id!r}")


def pending_actions(project_id: str | None = None) -> list[dict[str, Any]]:
    items = _load()
    out = [r for r in items if r.get("status") == "WAITING_FOR_USER"]
    if project_id:
        out = [r for r in out if r.get("projectId") == project_id]
    return out


def _load() -> list[dict[str, Any]]:
    path = _store_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _save(items: list[dict[str, Any]]) -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, indent=2), encoding="utf-8")


def _append(req: dict[str, Any]) -> None:
    items = _load()
    items.append(req)
    _save(items)
