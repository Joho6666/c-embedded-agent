"""Cross-cutting tests: artifact intelligence + embedded lint.

Uses the committed golden project (real firmware.elf) when the toolchain is
present; pure-text lint tests run everywhere.
"""

from __future__ import annotations

import pytest

from app.validation.lint import lint_project, lint_source
from app.tools.artifacts import analyze_artifacts, firmware_change

GOLDEN_LED = (
    __import__("pathlib").Path(__file__).resolve().parents[2] / "examples" / "golden" / "stm32f103_led"
)


# ---------------------------------------------------------------- lint

def test_lint_blocks_isr_delay():
    code = """
void USART1_IRQHandler(void) {
  if (flag) { HAL_Delay(10); }
}
"""
    findings = lint_source_from_string(code)
    rules = [f["rule"] for f in findings]
    assert "isr-blocking-call" in rules
    worst = max(f["severity"] for f in findings)
    assert worst == "ERROR"


def test_lint_flags_unsafe_string_and_stack_array():
    code = """
char *x;
void f(void) {
  char buf[512];
  gets(x);
}
"""
    findings = lint_source_from_string(code)
    rules = [f["rule"] for f in findings]
    assert "unsafe-gets" in rules
    assert "stack-heavy-array" in rules
    assert any(f["rule"] == "stack-heavy-array" and f["severity"] == "WARNING" for f in findings)


def test_lint_clean_code_is_ok():
    code = """
void USART1_IRQHandler(void) { flag = 1; }
int main(void) { while (1) {} }
volatile int flag = 0;
"""
    findings = lint_source_from_string(code)
    assert not [f for f in findings if f["severity"] == "ERROR"]


def test_lint_project_on_synthetic_tree(tmp_path):
    src = tmp_path / "Core" / "Src"
    src.mkdir(parents=True)
    (src / "main.c").write_text("void USART1_IRQHandler(void){ sprintf(buf, \"x\"); }\n", encoding="utf-8")
    result = lint_project(tmp_path)
    assert result["status"] == "FAIL"  # ERROR severity blocks
    assert result["counts"]["ERROR"] >= 1


def lint_source_from_string(code: str):
    import tempfile
    from pathlib import Path as P

    with tempfile.NamedTemporaryFile("w", suffix=".c", delete=False, encoding="utf-8") as f:
        f.write(code)
        name = f.name
    try:
        from pathlib import Path

        return lint_source(Path(name))
    finally:
        import os

        os.unlink(name)


# ---------------------------------------------------------------- artifacts

@pytest.mark.skipif(not GOLDEN_LED.is_dir(), reason="golden project missing")
def test_analyze_artifacts_on_real_golden():
    result = analyze_artifacts(GOLDEN_LED)
    assert result["available"] is True
    names = {s["name"] for s in result["sections"]}
    assert ".text" in names and ".bss" in names
    assert result["budgets"]["flash"]["used"] > 2000
    assert result["budgets"]["flash"]["status"] in {"OK", "WARNING"}
    assert result["largestSymbols"]


@pytest.mark.skipif(not GOLDEN_LED.is_dir(), reason="golden project missing")
def test_firmware_change_report_between_builds():
    import copy

    before = analyze_artifacts(GOLDEN_LED)
    after = copy.deepcopy(before)
    for s in after["sections"]:
        if s["name"] == ".text":
            s["bytes"] += 2048
    report = firmware_change(before, after)
    assert report["available"] is True
    assert report["flashDelta"] == 2048
    assert report["riskNotes"]


def test_firmware_change_requires_both_analyses(tmp_path):
    empty = {"available": False}
    assert firmware_change(empty, empty)["status"] == "UNAVAILABLE"
