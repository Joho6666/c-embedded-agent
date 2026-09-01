from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from app.config.settings import settings
from app.tools.gitutil import init_repo


def _ws_root() -> Path:
    p = settings.workspace_root
    if not p.is_absolute():
        p = Path.cwd() / p
    p.mkdir(parents=True, exist_ok=True)
    return p.resolve()


def create_project(name: str, mcu: str = "STM32F103C8T6", framework: str = "HAL") -> dict[str, Any]:
    pid = uuid.uuid4().hex[:12]
    dest = _ws_root() / pid
    src = settings.template_root
    if not src.is_absolute():
        src = Path.cwd() / src
    if not src.is_dir():
        raise FileNotFoundError(f"template missing: {src}")
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("*.elf", "*.hex", "*.bin", "*.o", "*.map", ".git"))
    meta = {
        "id": pid,
        "name": name,
        "platform": "STM32",
        "mcu": mcu,
        "framework": framework,
        "toolchain": "ARM_GCC",
        "board": "Blue Pill",
        "led": "PC13",
    }
    (dest / "project.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    init_repo_safe(dest)
    return meta


def init_repo_safe(dest: Path) -> None:
    try:
        init_repo(dest)
    except Exception:
        pass


def project_root(project_id: str) -> Path:
    dest = _ws_root() / project_id
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
