"""Error Memory IRQ fix: DMA handler must call HAL_DMA_IRQHandler with the real handle."""

from __future__ import annotations

from pathlib import Path

from app.tools.error_memory import apply_known_fix

IT_C = "#include \"stm32f1xx_it.h\"\n\nvoid NMI_Handler(void)\n{\n}\n"
IT_H = "#ifdef __cplusplus\nextern \"C\" {\n#endif\n\n#ifdef __cplusplus\n}\n#endif\n"


def _project(tmp_path: Path, *, with_handle: bool) -> None:
    (tmp_path / "Core" / "Src").mkdir(parents=True)
    (tmp_path / "Core" / "Inc").mkdir(parents=True)
    if with_handle:
        (tmp_path / "Core" / "Src" / "usart.c").write_text(
            "DMA_HandleTypeDef hdma_usart1_rx;\n"
            "\n"
            "static void MX_DMA_Init(void)\n"
            "{\n"
            "  hdma_usart1_rx.Instance = DMA1_Channel5;\n"
            "}\n",
            encoding="utf-8",
        )
    (tmp_path / "Core" / "Src" / "stm32f1xx_it.c").write_text(IT_C, encoding="utf-8")
    (tmp_path / "Core" / "Inc" / "stm32f1xx_it.h").write_text(IT_H, encoding="utf-8")


def test_dma_irq_fix_binds_handle_and_calls_hal(tmp_path: Path) -> None:
    _project(tmp_path, with_handle=True)
    out = apply_known_fix(tmp_path, "dma-handler-missing")
    assert out["applied"] is True
    text = (tmp_path / "Core" / "Src" / "stm32f1xx_it.c").read_text(encoding="utf-8")
    assert "extern DMA_HandleTypeDef hdma_usart1_rx;" in text
    assert "void DMA1_Channel5_IRQHandler(void)" in text
    assert "HAL_DMA_IRQHandler(&hdma_usart1_rx);" in text
    # the empty stub that would storm on hardware must be gone
    assert "known-fix stub: handler body" not in text


def test_dma_irq_fix_refuses_without_handle(tmp_path: Path) -> None:
    _project(tmp_path, with_handle=False)
    out = apply_known_fix(tmp_path, "dma-handler-missing")
    assert out["applied"] is False
    assert "manual fix required" in str(out.get("reason"))
    assert (tmp_path / "Core" / "Src" / "stm32f1xx_it.c").read_text(encoding="utf-8") == IT_C


def test_dma_irq_fix_skips_when_handler_already_present(tmp_path: Path) -> None:
    _project(tmp_path, with_handle=True)
    itc = tmp_path / "Core" / "Src" / "stm32f1xx_it.c"
    itc.write_text(IT_C + "\nvoid DMA1_Channel5_IRQHandler(void)\n{\n}\n", encoding="utf-8")
    out = apply_known_fix(tmp_path, "dma-handler-missing")
    assert out["applied"] is False
    assert "already present" in str(out.get("reason"))
