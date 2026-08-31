from pathlib import Path

import pytest

from app.workspace.paths import PathEscapeError, ProtectedPathError, assert_writable, resolve_in_root


def test_path_escape(tmp_path: Path):
    with pytest.raises(PathEscapeError):
        resolve_in_root(tmp_path, "../etc/passwd")


def test_protected_drivers():
    with pytest.raises(ProtectedPathError):
        assert_writable("Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal.c")


def test_protected_makefile_and_ld():
    with pytest.raises(ProtectedPathError):
        assert_writable("Makefile")
    with pytest.raises(ProtectedPathError):
        assert_writable("STM32F103C8Tx_FLASH.ld")
    with pytest.raises(ProtectedPathError):
        assert_writable("startup_stm32f103xb.s")


def test_allowed_core():
    assert assert_writable("Core/Src/main.c") == "Core/Src/main.c"
    assert assert_writable("Core/Inc/gpio.h") == "Core/Inc/gpio.h"


def test_advanced_allows_makefile():
    assert assert_writable("Makefile", advanced=True) == "Makefile"
