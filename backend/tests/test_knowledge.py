from app.tools.knowledge import retrieve_knowledge


def test_gpio_query_hits_notes():
    hits = retrieve_knowledge("STM32 GPIO PA5 HAL")
    assert hits
    titles = " ".join(h["title"] for h in hits)
    assert "gpio" in titles.lower() or "hal" in titles.lower()
