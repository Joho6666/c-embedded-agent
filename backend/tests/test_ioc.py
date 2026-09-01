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


def test_build_context_reads_ioc_analysis(tmp_path: Path) -> None:
    import json

    from app.agent.context import build_context, context_prompt

    analysis = parse_ioc((Path(__file__).resolve().parents[2] / "templates" / "bluepill.ioc").read_text(encoding="utf-8"), "bluepill.ioc")
    (tmp_path / "ioc-analysis.json").write_text(json.dumps(analysis), encoding="utf-8")
    (tmp_path / "Core" / "Src").mkdir(parents=True)
    (tmp_path / "Core" / "Src" / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
    ctx = build_context(tmp_path, iteration=0, prompt="USART1 每500ms发送 Hello")
    assert ctx["ioc"] is not None
    assert ctx["led"] == "PC13"
    assert "USART" in context_prompt(ctx)
    assert any(s.get("id") == "usart" for s in ctx["skills"])
