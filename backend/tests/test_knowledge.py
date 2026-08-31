from app.tools.knowledge import retrieve_knowledge


def test_gpio_query_hits_notes():
    hits = retrieve_knowledge("STM32 GPIO PC13 HAL")
    assert hits
    blob = " ".join(h["title"] + h.get("excerpt", "") + h.get("source", "") for h in hits).lower()
    assert "gpio" in blob or "hal" in blob


def test_citation_has_source():
    hits = retrieve_knowledge("USART1 PA9")
    assert hits
    assert any(h.get("source") for h in hits)
