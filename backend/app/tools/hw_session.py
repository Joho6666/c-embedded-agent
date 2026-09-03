from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT = {
    "debugger": "ST-Link",
    "serialDevice": None,
    "baud": 115200,
    "board": "Blue Pill",
    "mcu": "STM32F103C8T6",
}


def session_path(root: Path) -> Path:
    return root / "hardware-session.json"


def load_session(root: Path) -> dict[str, Any]:
    p = session_path(root)
    data = dict(DEFAULT)
    if p.is_file():
        try:
            loaded = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data.update({k: loaded[k] for k in DEFAULT if k in loaded})
        except json.JSONDecodeError:
            pass
    meta = root / "project.json"
    if meta.is_file():
        try:
            pj = json.loads(meta.read_text(encoding="utf-8"))
            data["mcu"] = data.get("mcu") or pj.get("mcu") or DEFAULT["mcu"]
            data["board"] = data.get("board") or pj.get("board") or DEFAULT["board"]
        except json.JSONDecodeError:
            pass
    return data


def save_session(root: Path, **kwargs: Any) -> dict[str, Any]:
    data = load_session(root)
    for k, v in kwargs.items():
        if k in DEFAULT:
            data[k] = v
    session_path(root).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data
