from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

from app.config.settings import settings
from app.platforms.registry import default_registry
from app.tools.gitutil import init_repo


PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _ws_root() -> Path:
    p = settings.workspace_root
    if not p.is_absolute():
        p = Path.cwd() / p
    p.mkdir(parents=True, exist_ok=True)
    return p.resolve()


def create_project(
    name: str,
    mcu: str | None = "STM32F103C8T6",
    framework: str | None = "HAL",
    *,
    platform: str | None = None,
    board: str | None = None,
    adapter_id: str | None = None,
    toolchain: str | None = None,
) -> dict[str, Any]:
    resolution = default_registry(settings.repo_root).resolve_explicit(
        adapter_id=adapter_id, platform=platform, mcu=mcu, framework=framework
    )
    if resolution.status != "resolved" or resolution.adapter is None:
        raise ValueError(resolution.reason or "unsupported platform")
    pid = uuid.uuid4().hex[:12]
    dest = _ws_root() / pid
    result = resolution.adapter.create_template(
        dest,
        name=name,
        board=board,
        metadata={"id": pid, **({"toolchain": toolchain} if toolchain else {})},
    )
    if not result.success:
        raise ValueError(result.reason or "project template creation failed")
    meta = dict(result.data.get("metadata") or {})
    init_repo_safe(dest)
    return meta


def init_repo_safe(dest: Path) -> None:
    try:
        init_repo(dest)
    except Exception:
        pass


def project_root(project_id: str) -> Path:
    if not PROJECT_ID_RE.fullmatch(project_id or ""):
        raise FileNotFoundError(project_id)
    workspace = _ws_root()
    dest = (workspace / project_id).resolve()
    if dest.parent != workspace:
        raise FileNotFoundError(project_id)
    if not dest.is_dir():
        raise FileNotFoundError(project_id)
    return dest


def list_projects() -> list[dict[str, Any]]:
    items = []
    for d in _ws_root().iterdir():
        if not d.is_dir():
            continue
        meta = d / "project.json"
        if meta.is_file():
            items.append(json.loads(meta.read_text(encoding="utf-8")))
    return items
