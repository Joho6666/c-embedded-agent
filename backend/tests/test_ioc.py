from pathlib import Path

from app.tools.ioc import parse_ioc


def test_bluepill_ioc_parses_clock_and_pins() -> None:
    root = Path(__file__).resolve().parents[2]
    text = (root / "templates" / "bluepill.ioc").read_text(encoding="utf-8")
    analysis = parse_ioc(text, "bluepill.ioc")
    assert analysis["mcu"] == "STM32F103C8Tx"
    assert analysis["family"] == "STM32F1"
    assert analysis["board"] == "Blue Pill"
    assert analysis["clock"]["sysclkHz"] == 72_000_000
    assert analysis["clock"]["hseHz"] == 8_000_000
    signals = {p["pin"]: p["signal"] for p in analysis["pins"]}
    assert signals["PA9"] == "USART1_TX"
    assert signals["PA10"] == "USART1_RX"
    assert signals["PA0"] == "TIM2_CH1"
    assert signals["PC13"] == "GPIO_Output"
    assert any(u["name"].startswith("USART") for u in analysis["usart"])
