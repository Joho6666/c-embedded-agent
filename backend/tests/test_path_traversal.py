from pathlib import Path

import pytest

from app.workspace.paths import PathEscapeError, ProtectedPathError, assert_writable, resolve_in_root


def test_path_escape(tmp_path: Path):
    with pytest.raises(PathEscapeError):
        resolve_in_root(tmp_path, "../etc/passwd")


def test_protected_files():
    test_protected_drivers()
    test_protected_makefile_and_ld()
    test_protected_middlewares_and_ioc()


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


def test_protected_middlewares_and_ioc():
    with pytest.raises(ProtectedPathError):
        assert_writable("Middlewares/FreeRTOS/Source/tasks.c")
    with pytest.raises(ProtectedPathError):
        assert_writable("project.ioc")


def test_symlink_escape(tmp_path: Path):
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.c"
    secret.write_text("nope\n", encoding="utf-8")
    root = tmp_path / "proj"
    root.mkdir()
    link = root / "Core"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not available")
    with pytest.raises(PathEscapeError):
        resolve_in_root(root, "Core/secret.c")
