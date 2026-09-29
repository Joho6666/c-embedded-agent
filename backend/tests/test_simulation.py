"""Simulation layer tests — Renode adapter (real run when installed)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.hardware.simulation import list_adapters
from app.hardware.simulation.renode import RenodeAdapter, find_renode

FIXTURES = Path(__file__).parent / "fixtures"


def test_adapter_list_is_honest():
    listed = {a["id"]: a for a in list_adapters()}
    assert "renode" in listed
    if find_renode() is None:
        assert listed["renode"]["adapterStatus"] == "NOT_INSTALLED"


def test_run_without_renode_is_honest_unavailable(tmp_path: Path, monkeypatch):
    elf = tmp_path / "x.elf"
    elf.write_bytes(b"not really")
    adapter = RenodeAdapter()
    monkeypatch.setattr("app.hardware.simulation.renode.find_renode", lambda: None)
    result = adapter.run(str(elf))
    assert result["available"] is False
    assert result["status"] == "UNAVAILABLE"
    assert "NOT_RUN" in result["reason"]


def test_run_with_missing_elf_fails(tmp_path: Path, monkeypatch):
    adapter = RenodeAdapter(timeout_s=5)
    monkeypatch.setattr("app.tools.toolchain.prepend_toolchain_path", lambda: None)
    if find_renode() is None:
        pytest.skip("Renode not installed")
    result = adapter.run(str(tmp_path / "nope.elf"), timeout_s=5)
    assert result["status"] == "FAIL"


@pytest.mark.skipif(find_renode() is None, reason="Renode not installed")
def test_renode_real_spike_stm32f103():
    """The real Level-2 spike: our STM32F103 ELF runs in Renode and emits the
    evidence token over UART (docs/RENODE_SPIKE.md)."""
    elf = FIXTURES / "renode_spike" / "sim_uart.elf"
    if not elf.is_file():
        pytest.skip("spike ELF not built (needs arm-none-eabi-gcc)")
    adapter = RenodeAdapter(timeout_s=30)
    result = adapter.run(str(elf), expect="CEA:SIM:PASS", timeout_s=30)
    assert result["available"] is True
    assert result["status"] == "SUCCESS"
    assert result["expectMatch"] is True
    assert any("CEA:SIM:PASS" in ln for ln in result["uartLines"])
    assert result["evidence"]["level"] == "SIMULATION"
