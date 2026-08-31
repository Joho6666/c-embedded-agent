from pathlib import Path

from app.config.settings import settings
from app.workspace.manager import create_project, project_root


def test_project_create_uses_official_template(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "workspace_root", tmp_path)
    meta = create_project("LED", "STM32F103C8T6", "HAL")
    root = project_root(meta["id"])
    assert (root / "Core/Src/main.c").is_file()
    assert (root / "Makefile").is_file()
    main = (root / "Core/Src/main.c").read_text(encoding="utf-8")
    assert "PC13" in (root / "Core/Inc/main.h").read_text(encoding="utf-8") or "LED_Pin" in main
    assert (root / "Drivers/CMSIS/Include/core_cm3.h").is_file()
    assert (root / "Drivers/CMSIS/Device/ST/STM32F1xx/Include/stm32f103xb.h").is_file()
    assert "stm32f1xx_hal_gpio.c" in str(list((root / "Drivers/STM32F1xx_HAL_Driver/Src").glob("*.c")))
