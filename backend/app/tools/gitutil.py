from __future__ import annotations

import subprocess
from pathlib import Path


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
        shell=False,
    )


def init_repo(root: Path) -> None:
    if (root / ".git").exists():
        return
    _git(root, "init")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "initial snapshot", "--allow-empty")


def snapshot(root: Path, message: str) -> str:
    if not (root / ".git").exists():
        init_repo(root)
    _git(root, "add", "-A")
    _git(root, "commit", "-m", message, "--allow-empty")
    r = _git(root, "rev-parse", "HEAD")
    return (r.stdout or "").strip()


def restore_snapshot(root: Path, sha: str) -> bool:
    if not sha:
        return False
    r = _git(root, "reset", "--hard", sha)
    return r.returncode == 0
