import os
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from app.config.settings import settings
from app.db import connect
from app.tools import knowledge
from app.tools.knowledge import ingest_pdf, retrieve_knowledge


def test_gpio_query_hits_notes():
    hits = retrieve_knowledge("STM32 GPIO PC13 HAL")
    assert hits
    blob = " ".join(h["title"] + h.get("excerpt", "") + h.get("source", "") for h in hits).lower()
    assert "gpio" in blob or "hal" in blob


def test_citation_has_source():
    hits = retrieve_knowledge("USART1 PA9")
    assert hits
    assert any(h.get("source") for h in hits)


@pytest.fixture
def isolated_kb(tmp_path: Path, monkeypatch):
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "gpio.md").write_text(
        "---\nsource: RM0008\nsection: GPIO\n---\nGPIO PC13 drives the Blue Pill LED.\n", encoding="utf-8"
    )
    monkeypatch.setattr(settings, "workspace_root", tmp_path / "ws")
    monkeypatch.setattr(settings, "knowledge_root", notes)
    return notes


def _install_fake_pypdf(monkeypatch, pages: list[str]) -> None:
    page_objs = [SimpleNamespace(extract_text=lambda text=text: text) for text in pages]
    fake = ModuleType("pypdf")
    fake.PdfReader = lambda path: SimpleNamespace(pages=page_objs)
    monkeypatch.setitem(sys.modules, "pypdf", fake)


def test_pdf_pages_survive_later_queries(isolated_kb: Path, monkeypatch, tmp_path: Path):
    _install_fake_pypdf(monkeypatch, ["The DMA1 channel five serves USART1 RX requests in circular mode."])
    retrieve_knowledge("GPIO PC13")
    # Same source name as the markdown note: note sync must not delete PDF rows.
    assert ingest_pdf(tmp_path / "rm0008.pdf", source="RM0008") == 1
    for _ in range(2):
        hits = retrieve_knowledge("circular DMA1")
        assert any(h["page"] == "1" and "circular" in h["excerpt"] for h in hits), hits
    assert any("PC13" in h["excerpt"] for h in retrieve_knowledge("PC13"))


def test_markdown_sync_is_incremental(isolated_kb: Path, monkeypatch):
    parsed: list[str] = []
    original = knowledge._parse_note
    monkeypatch.setattr(knowledge, "_parse_note", lambda p: parsed.append(p.name) or original(p))
    assert knowledge.ingest_markdown() == 1
    assert knowledge.ingest_markdown() == 0
    retrieve_knowledge("GPIO")
    assert parsed == ["gpio.md"]

    (isolated_kb / "gpio.md").write_text("GPIO PC13 now toggles every 250 ms.\n", encoding="utf-8")
    os.utime(isolated_kb / "gpio.md", ns=(1, 1))
    assert knowledge.ingest_markdown() == 1
    hits = retrieve_knowledge("toggles")
    assert len([h for h in hits if h["title"] == "gpio"]) == 1
    assert "250 ms" in hits[0]["excerpt"]

    (isolated_kb / "gpio.md").unlink()
    knowledge.ingest_markdown()
    with connect() as con:
        assert con.execute("SELECT count(*) FROM knowledge_fts").fetchone()[0] == 0
