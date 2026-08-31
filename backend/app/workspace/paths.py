from __future__ import annotations

from pathlib import Path


class PathEscapeError(ValueError):
    pass


def resolve_in_root(root: Path, rel: str) -> Path:
    root = root.resolve()
    raw = (root / rel).resolve()
    if raw != root and root not in raw.parents:
        raise PathEscapeError(f"path escapes workspace: {rel}")
    return raw
