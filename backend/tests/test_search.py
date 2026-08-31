from pathlib import Path

from app.tools.search import search_code


def test_search_finds_gpio(tmp_path: Path):
    (tmp_path / "main.c").write_text("HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_5);\n", encoding="utf-8")
    hits = search_code(tmp_path, "GPIO_PIN_5")
    assert hits
    assert "main.c:1" in hits[0]
