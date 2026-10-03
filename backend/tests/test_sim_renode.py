"""Renode behavioural simulation: suite generation, evidence rules, and (when
Renode is installed) real runs that tell correct firmware from wrong firmware."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from app.sim import renode
from app.sim.renode import LedBlinkCheck, UartExpectCheck, build_robot_suite, simulate
from app.tools.toolchain import prepend_toolchain_path

REPO = Path(__file__).resolve().parents[2]
USART_GOLDEN = REPO / "examples" / "golden" / "stm32f103_usart"


def test_suite_contains_board_models_and_one_case_per_check(tmp_path: Path) -> None:
    elf = tmp_path / "firmware.elf"
    suite = build_robot_suite(elf, [LedBlinkCheck(), UartExpectCheck(expect="CEA:USART:PASS")])
    assert "stm32f1_rcc.py" in suite and "register_file.py" in suite
    assert "Miscellaneous.BitBanding" in suite
    assert "ledc13: Miscellaneous.LED @ gpioPortC 13" in suite
    assert "onDuration=0.5    offDuration=0.5" in suite
    assert "Wait For Line On Uart    CEA:USART:PASS" in suite
    assert "\\" not in re.search(r"LoadELF @(\S+)", suite).group(1)
    assert suite.count("    Create Board\n") == 2


def test_uart_text_is_escaped_for_robot(tmp_path: Path) -> None:
    suite = build_robot_suite(tmp_path / "f.elf", [UartExpectCheck(expect="a  b ${x} c\\d")])
    assert "a ${SPACE}b \\${x} c\\\\d" in suite


def test_missing_renode_is_unavailable_never_pass(tmp_path: Path, monkeypatch) -> None:
    elf = tmp_path / "firmware.elf"
    elf.write_bytes(b"\x7fELF")
    monkeypatch.setattr(renode, "find_renode", lambda: None)
    result = simulate(elf, [LedBlinkCheck()])
    assert result.status == "UNAVAILABLE" and not result.success
    assert simulate(elf, []).status == "UNAVAILABLE"
    assert simulate(tmp_path / "missing.elf", [LedBlinkCheck()]).status == "FAIL"


def _renode_ready() -> bool:
    prepend_toolchain_path()
    return (
        renode.find_renode() is not None
        and renode.find_test_python() is not None
        and shutil.which("arm-none-eabi-gcc") is not None
        and shutil.which("make") is not None
    )


requires_renode = pytest.mark.skipif(not _renode_ready(), reason="Renode + ARM GCC not available")


def _build_variant(tmp_path: Path, name: str, edits: dict[str, tuple[str, str]]) -> Path:
    project = tmp_path / name
    shutil.copytree(USART_GOLDEN, project, ignore=shutil.ignore_patterns("*.o", "*.d", "*.elf", "*.hex", "*.bin", "*.map", "build"))
    for rel, (old, new) in edits.items():
        path = project / rel
        text = path.read_text(encoding="utf-8")
        assert old in text
        path.write_text(text.replace(old, new), encoding="utf-8")
    subprocess.run(["make", "-j4"], cwd=project, check=True, capture_output=True)
    return project / "firmware.elf"


@requires_renode
def test_simulation_passes_correct_and_catches_wrong_behaviour(tmp_path: Path) -> None:
    checks = [LedBlinkCheck(port="C", pin=13, on=0.5, off=0.5), UartExpectCheck(peripheral="usart1", expect="Hello")]

    good = simulate(_build_variant(tmp_path, "good", {}), checks, results_dir=tmp_path / "good-out")
    assert good.status == "PASS", good.reason

    # Both variants compile cleanly; only behaviour differs.
    fast = simulate(
        _build_variant(tmp_path, "fast", {"Core/Src/main.c": ("HAL_Delay(500)", "HAL_Delay(250)")}),
        checks,
        results_dir=tmp_path / "fast-out",
    )
    assert fast.status == "FAIL"
    assert [c["status"] for c in fast.checks] == ["FAIL", "PASS"]

    wrong_uart = simulate(
        _build_variant(tmp_path, "uart2", {"Core/Src/usart.c": ("Instance = USART1", "Instance = USART2")}),
        checks,
        results_dir=tmp_path / "uart2-out",
    )
    assert wrong_uart.status == "FAIL"
    assert [c["status"] for c in wrong_uart.checks] == ["PASS", "FAIL"]
