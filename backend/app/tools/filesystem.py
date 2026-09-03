from __future__ import annotations

from pathlib import Path

from app.workspace.paths import assert_writable, resolve_in_root

TEXT_MAX = 200_000


def list_files(root: Path) -> list[str]:
    root = root.resolve()
    out: list[str] = []
    for p in root.rglob("*"):
        if p.is_file() and ".git" not in p.parts:
            out.append(str(p.relative_to(root)).replace("\\", "/"))
    return sorted(out)


def read_file(root: Path, rel: str) -> str:
    path = resolve_in_root(root, rel)
    if not path.is_file():
        raise FileNotFoundError(rel)
    data = path.read_bytes()
    if len(data) > TEXT_MAX:
        data = data[:TEXT_MAX]
    return data.decode("utf-8", errors="replace")


def write_file(root: Path, rel: str, content: str, *, advanced: bool = False) -> None:
    norm = assert_writable(rel, advanced=advanced)
    path = resolve_in_root(root, norm)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
