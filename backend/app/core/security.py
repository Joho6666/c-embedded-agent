from __future__ import annotations

import os
from pathlib import Path

from app.workspace.paths import PathEscapeError, ProtectedPathError, assert_writable, resolve_in_root

# Process-local cap so an agent cannot loop-flash hardware.
_FLASH_COUNT = 0
_FLASH_MAX = 8


class ProjectRootError(ValueError):
    pass


class FlashRateLimitError(RuntimeError):
    pass


def resolve_project_root(project_root: str | Path) -> Path:
    raw = str(project_root or "").strip()
    if not raw or "\x00" in raw:
        raise ProjectRootError("project_root is required")
    root = Path(raw).expanduser().resolve()
    if not root.is_dir():
        raise ProjectRootError(f"project_root is not a directory: {root}")
    allowed = os.environ.get("CEA_ALLOWED_ROOTS", "").strip()
    if allowed:
        prefixes = [Path(p.strip()).expanduser().resolve() for p in allowed.split(",") if p.strip()]
        if prefixes and not any(root == p or _is_relative_to(root, p) for p in prefixes):
            raise ProjectRootError(f"project_root is outside CEA_ALLOWED_ROOTS: {root}")
    return root


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def resolve_under(root: Path, rel: str) -> Path:
    return resolve_in_root(root, rel)


def require_writable(rel: str, *, advanced: bool = False) -> str:
    return assert_writable(rel, advanced=advanced)


def check_flash_budget() -> None:
    if _FLASH_COUNT >= _FLASH_MAX:
        raise FlashRateLimitError(
            f"flash rate limit: {_FLASH_COUNT} attempts in this process (max {_FLASH_MAX})"
        )


def note_flash() -> int:
    global _FLASH_COUNT
    _FLASH_COUNT += 1
    return _FLASH_COUNT


def flash_attempts() -> int:
    return _FLASH_COUNT


def reset_flash_budget_for_tests() -> None:
    global _FLASH_COUNT
    _FLASH_COUNT = 0


__all__ = [
    "FlashRateLimitError",
    "PathEscapeError",
    "ProjectRootError",
    "ProtectedPathError",
    "assert_writable",
    "check_flash_budget",
    "flash_attempts",
    "note_flash",
    "require_writable",
    "reset_flash_budget_for_tests",
    "resolve_in_root",
    "resolve_project_root",
    "resolve_under",
]
