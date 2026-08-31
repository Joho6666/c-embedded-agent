from __future__ import annotations

from pathlib import Path


def search_code(root: Path, query: str, limit: int = 40) -> list[str]:
    q = query.strip()
    if not q or len(q) > 80:
        return []
    hits: list[str] = []
    root = root.resolve()
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in {".c", ".h", ".s", ".ld", ".md", ".txt"}:
            continue
        if ".git" in p.parts:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(p.relative_to(root)).replace("\\", "/")
        for i, line in enumerate(text.splitlines(), 1):
            if q in line:
                hits.append(f"{rel}:{i}:{line.strip()}")
                if len(hits) >= limit:
                    return hits
    return hits
