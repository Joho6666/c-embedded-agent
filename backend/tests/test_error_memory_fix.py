from pathlib import Path

from app.tools.error_memory import apply_known_fix


def test_apply_uart_fix_inserts_makefile_and_macro(tmp_path: Path) -> None:
    (tmp_path / "Core" / "Inc").mkdir(parents=True)
    (tmp_path / "Makefile").write_text(
        "C_SOURCES = \\\n"
        "\tDrivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_gpio.c\n",
        encoding="utf-8",
    )
    (tmp_path / "Core" / "Inc" / "stm32f1xx_hal_conf.h").write_text(
        "/* #define HAL_UART_MODULE_ENABLED */\n#define HAL_GPIO_MODULE_ENABLED\n",
        encoding="utf-8",
    )
    out = apply_known_fix(tmp_path, "hal-uart-init-undef")
    assert out["applied"] is True
    mk = (tmp_path / "Makefile").read_text(encoding="utf-8")
    assert "stm32f1xx_hal_uart.c" in mk
    conf = (tmp_path / "Core" / "Inc" / "stm32f1xx_hal_conf.h").read_text(encoding="utf-8")
    assert "#define HAL_UART_MODULE_ENABLED" in conf
    assert "/* #define HAL_UART_MODULE_ENABLED */" not in conf


def test_unknown_error_id_not_applied(tmp_path: Path) -> None:
    out = apply_known_fix(tmp_path, "no-such-fix")
    assert out["applied"] is False
