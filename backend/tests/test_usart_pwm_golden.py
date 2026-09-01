import sys
from pathlib import Path

import pytest

from app.tools.compiler import compile_project
from app.tools.detect import gcc_installed, make_installed

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "examples" / "golden"))
from sync_overlay import sync  # noqa: E402

pytestmark = pytest.mark.skipif(not gcc_installed() or not make_installed(), reason="ARM GCC or make missing")


def test_golden_usart_builds():
    sync("usart", ["Core/Src/usart.c"])
    root = REPO / "examples" / "golden" / "stm32f103_usart"
    result = compile_project(root)
    assert result["success"], result.get("combined", "")[-2000:]
    assert (root / "firmware.elf").is_file()


def test_golden_pwm_builds():
    sync("pwm", ["Core/Src/tim.c"])
    root = REPO / "examples" / "golden" / "stm32f103_pwm"
    result = compile_project(root)
    assert result["success"], result.get("combined", "")[-2000:]
    assert (root / "firmware.elf").is_file()
