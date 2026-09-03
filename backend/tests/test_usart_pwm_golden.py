import sys
from pathlib import Path

import pytest

from app.tools.compiler import compile_project
from app.tools.detect import gcc_installed, make_installed

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "examples" / "golden"))
from sync_overlay import GOLDENS, sync  # noqa: E402

pytestmark = pytest.mark.skipif(not gcc_installed() or not make_installed(), reason="ARM GCC or make missing")


@pytest.mark.parametrize("name", sorted(GOLDENS.keys()))
def test_golden_builds(name: str):
    sync(name, GOLDENS[name])
    root = REPO / "examples" / "golden" / f"stm32f103_{name}"
    result = compile_project(root)
    assert result["success"], result.get("combined", "")[-2000:]
    assert (root / "firmware.elf").is_file()
    assert (root / "firmware.hex").is_file()
    assert (root / "firmware.bin").is_file()


def test_golden_usart_builds():
    test_golden_builds("usart")


def test_golden_pwm_builds():
    test_golden_builds("pwm")
