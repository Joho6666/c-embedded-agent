from pathlib import Path

from app.tools.error_memory import apply_known_fix, match_known_errors
from app.tools.hal_modules import register_hal_module


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


def test_known_fix(tmp_path: Path) -> None:
    test_apply_uart_fix_inserts_makefile_and_macro(tmp_path)


def test_known_fix_adc_and_i2c(tmp_path: Path) -> None:
    (tmp_path / "Core" / "Inc").mkdir(parents=True)
    (tmp_path / "Makefile").write_text(
        "C_SOURCES = \\\n"
        "\tDrivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_gpio.c\n",
        encoding="utf-8",
    )
    (tmp_path / "Core" / "Inc" / "stm32f1xx_hal_conf.h").write_text(
        "#define HAL_GPIO_MODULE_ENABLED\n",
        encoding="utf-8",
    )
    adc = apply_known_fix(tmp_path, "hal-adc-init-undef")
    assert adc["applied"] is True
    i2c = apply_known_fix(tmp_path, "hal-i2c-init-undef")
    assert i2c["applied"] is True
    mk = (tmp_path / "Makefile").read_text(encoding="utf-8")
    assert "stm32f1xx_hal_adc.c" in mk
    assert "stm32f1xx_hal_i2c.c" in mk


def test_register_hal_module_dedupes(tmp_path: Path) -> None:
    (tmp_path / "Core" / "Inc").mkdir(parents=True)
    (tmp_path / "Makefile").write_text(
        "C_SOURCES = \\\n"
        "\tDrivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_uart.c \\\n"
        "\tDrivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_gpio.c\n",
        encoding="utf-8",
    )
    (tmp_path / "Core" / "Inc" / "stm32f1xx_hal_conf.h").write_text(
        "#define HAL_UART_MODULE_ENABLED\n",
        encoding="utf-8",
    )
    first = register_hal_module(tmp_path, "UART")
    second = register_hal_module(tmp_path, "UART")
    mk = (tmp_path / "Makefile").read_text(encoding="utf-8")
    assert mk.count("stm32f1xx_hal_uart.c") == 1
    assert first["ok"] is True
    assert second["applied"] is False


def test_match_known_errors_signatures() -> None:
    hits = match_known_errors("undefined reference to HAL_ADC_Init")
    assert any(h["id"] == "hal-adc-init-undef" for h in hits)
    hits = match_known_errors("undefined reference to HAL_SPI_Init")
    assert any(h["id"] == "hal-spi-init-undef" for h in hits)
    hits = match_known_errors("undefined reference to DMA1_Channel5_IRQHandler")
    assert any(h["id"] == "dma-handler-missing" for h in hits)


def test_structured_error_memory_verified_count() -> None:
    from app.tools.error_memory import get_error, mark_fix_result

    item = get_error("hal-uart-init-undef")
    assert item is not None
    assert "error_signature" in item
    assert "platform" in item
    assert "confidence" in item
    assert "verified_count" in item
    initial_verified = item["verified_count"]

    # Success increments verified_count
    mark_fix_result("hal-uart-init-undef", success=True)
    item_after_ok = get_error("hal-uart-init-undef")
    assert item_after_ok["verified_count"] == initial_verified + 1
    assert item_after_ok["last_verified"] is not None

    # Failure does NOT increment verified_count
    mark_fix_result("hal-uart-init-undef", success=False)
    item_after_fail = get_error("hal-uart-init-undef")
    assert item_after_fail["verified_count"] == initial_verified + 1

    # Failed compile or validator does NOT increment verified_count
    mark_fix_result("hal-uart-init-undef", success=True, compile_success=False, validator_pass=True)
    item_after_compile_fail = get_error("hal-uart-init-undef")
    assert item_after_compile_fail["verified_count"] == initial_verified + 1

    # Full pass (patch + compile + validator) increments verified_count and updates last_success_sha
    mark_fix_result("hal-uart-init-undef", success=True, compile_success=True, validator_pass=True, git_sha="abc1234")
    item_after_full = get_error("hal-uart-init-undef")
    assert item_after_full["verified_count"] == initial_verified + 2
    assert item_after_full["last_success_sha"] == "abc1234"
    assert item_after_full["success_count"] >= 2
    assert item_after_full["confidence"] > 0.0

