from __future__ import annotations

from pathlib import Path

from app.config.settings import settings


def retrieve_knowledge(query: str, k: int = 3) -> list[dict[str, str]]:
    root = settings.knowledge_root
    if not root.is_absolute():
        root = Path.cwd() / root
    if not root.is_dir():
        return []
    tokens = [t.lower() for t in query.replace("/", " ").split() if len(t) > 1]
    scored: list[tuple[int, Path, str]] = []
    for p in root.rglob("*"):
        if p.suffix.lower() not in {".md", ".txt"}:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        low = text.lower()
        score = sum(low.count(t) for t in tokens) if tokens else 1
        if score:
            scored.append((score, p, text[:1200]))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for score, p, excerpt in scored[:k]:
        out.append({"title": p.stem, "path": str(p.name), "excerpt": excerpt, "score": str(score)})
    return out
