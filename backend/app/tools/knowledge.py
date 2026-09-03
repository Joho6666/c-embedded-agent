from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from app.config.settings import settings
from app.db import connect

FRONT_MATTER_KEYS = ("source", "page", "section", "mcu", "type", "title")


def _parse_note(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    meta: dict[str, str] = {
        "title": path.stem,
        "source": path.stem,
        "page": "",
        "section": path.stem,
        "mcu": "STM32F103",
        "type": "note",
        "body": text,
    }
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm, body = parts[1], parts[2]
            for line in fm.splitlines():
                if ":" not in line:
                    continue
                k, v = line.split(":", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k in FRONT_MATTER_KEYS:
                    meta[k] = v
            meta["body"] = body.strip()
            if not meta.get("title"):
                meta["title"] = path.stem
    return meta


def ingest_markdown() -> int:
    root = settings.knowledge_root
    if not root.is_absolute():
        root = Path.cwd() / root
    if not root.is_dir():
        return 0
    n = 0
    with connect() as con:
        con.execute("DELETE FROM knowledge_fts")
        for p in root.rglob("*"):
            if p.suffix.lower() not in {".md", ".txt"}:
                continue
            note = _parse_note(p)
            con.execute(
                """INSERT INTO knowledge_fts(title, body, source, section, page, mcu, kind)
                   VALUES(?,?,?,?,?,?,?)""",
                (
                    note["title"],
                    note["body"],
                    note["source"],
                    note["section"],
                    note["page"],
                    note["mcu"],
                    note["type"],
                ),
            )
            n += 1
    return n


def ingest_pdf(pdf_path: Path, *, source: str, mcu: str = "STM32F103", kind: str = "reference_manual") -> int:
    """Extract text per page. Requires pypdf if installed; otherwise returns 0."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return 0
    reader = PdfReader(str(pdf_path))
    n = 0
    with connect() as con:
        for i, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if len(text) < 40:
                continue
            con.execute(
                """INSERT INTO knowledge_fts(title, body, source, section, page, mcu, kind)
                   VALUES(?,?,?,?,?,?,?)""",
                (f"{source} p.{i}", text[:8000], source, "", str(i), mcu, kind),
            )
            n += 1
    return n


def _fts_query(query: str) -> str:
    tokens = [t for t in query.replace("/", " ").replace("-", " ").split() if t.isalnum() and len(t) > 1]
    return " ".join(tokens)[:200]


def retrieve_knowledge(query: str, k: int = 4) -> list[dict[str, str]]:
    q = (query or "").strip()
    if not q:
        return []
    ingest_markdown()
    fts = _fts_query(q) or q
    try:
        with connect() as con:
            rows = con.execute(
                """SELECT title, body, source, section, page, mcu, kind,
                          bm25(knowledge_fts) AS rank
                   FROM knowledge_fts
                   WHERE knowledge_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (fts, k),
            ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    if not rows:
        return _keyword_fallback(q, k)
    out = []
    for r in rows:
        out.append(
            {
                "title": r["title"],
                "path": r["source"],
                "excerpt": (r["body"] or "")[:1200],
                "score": str(round(abs(float(r["rank"])), 3)),
                "source": r["source"],
                "section": r["section"] or "",
                "page": r["page"] or "",
                "mcu": r["mcu"] or "STM32F103",
                "type": r["kind"] or "note",
            }
        )
    return out


def _keyword_fallback(query: str, k: int) -> list[dict[str, str]]:
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
        out.append(
            {
                "title": p.stem,
                "path": p.name,
                "excerpt": excerpt,
                "score": str(score),
                "source": p.stem,
                "section": p.stem,
                "page": "",
                "mcu": "STM32F103",
                "type": "note",
            }
        )
    return out


def format_citation(hit: dict[str, str]) -> str:
    parts = [hit.get("source") or hit.get("title") or "knowledge"]
    if hit.get("section"):
        parts.append(hit["section"])
    if hit.get("page"):
        parts.append(f"Page {hit['page']}")
    return " · ".join(parts)
