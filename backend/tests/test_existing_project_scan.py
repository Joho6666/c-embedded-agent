from pathlib import Path

from app.tools.project_scan import scan_existing_project


def test_existing_project_scan(tmp_path: Path) -> None:
    (tmp_path / "Core" / "Src").mkdir(parents=True)
    (tmp_path / "Drivers" / "STM32F1xx_HAL_Driver" / "Src").mkdir(parents=True)
    (tmp_path / "Middlewares").mkdir()
    (tmp_path / "Core" / "Src" / "main.c").write_text("int main(void){return 0;}\n", encoding="utf-8")
    (tmp_path / "Drivers" / "STM32F1xx_HAL_Driver" / "Src" / "stm32f1xx_hal.c").write_text("void HAL_Init(void){}\n", encoding="utf-8")
    (tmp_path / "startup_stm32f103xb.s").write_text(".syntax unified\n", encoding="utf-8")
    (tmp_path / "STM32F103C8Tx_FLASH.ld").write_text("MEMORY {}\n", encoding="utf-8")
    (tmp_path / "Makefile").write_text("all:\n\t@echo ok\n", encoding="utf-8")
    (tmp_path / "board.ioc").write_text("Mcu.Name=STM32F103C8Tx\nMcu.Family=STM32F1\n", encoding="utf-8")
    scan = scan_existing_project(tmp_path)
    assert scan["ok"] is True
    assert scan["framework"] == "HAL"
    assert scan["cubemx"] is True
    assert scan["buildSystem"] == "make"
    assert scan["ioc"] == "board.ioc"
    assert any(f.endswith("main.c") for f in scan["coreFiles"])
    assert scan["startup"]
