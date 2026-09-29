"""Hardware debug layer tests: probe adapters, crash decoder, live workflow.

All hardware-dependent behavior uses fakes/monkeypatched tools; honest
UNAVAILABLE paths are asserted just as hard as the success paths.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config.settings import settings
from app.hardware import crash, debug_workflow
from app.hardware import probes as probe_registry
from app.hardware.probes.base import DebugProbeAdapter
from app.hardware.probes import openocd as openocd_mod
from app.hardware.probes.openocd import OpenOCDAdapter


# ---------------------------------------------------------------- regmap

def test_regmap_resolves_named_addresses():
    from app.hardware import regmap

    assert regmap.resolve("CFSR") == "0xE000ED28"
    assert regmap.resolve("gpioC_odr".upper()) == "0x4001100C"
    assert regmap.resolve("USART1_SR") == "0x40013800"
    assert regmap.resolve("0xE000ED28") is None  # raw addresses are not in the named map
    assert regmap.addresses_for("RCC")["RCC_CR"] == "0x40021000"


# ---------------------------------------------------------------- crash decoder

def test_decode_invstate_usagefault():
    ev = crash.decode_fault(cfsr="0x00020000", hfsr="0x40000000", pc="0x08001234", sp="0x20001000")
    names = {f["name"] for f in ev["flags"]}
    assert "INVSTATE" in names and "FORCED" in names
    assert any("function pointer" in c for c in ev["possibleCauses"])
    assert ev["pc"] == "0x08001234"


def test_decode_precise_busfault_on_peripheral_without_clock():
    ev = crash.decode_fault(cfsr=0x00008200, bfar="0x40021000")  # PRECISERR | BFARVALID
    flags = {f["name"] for f in ev["flags"]}
    assert {"PRECISERR", "BFARVALID"} <= flags
    assert "precise bus fault at 0x40021000" in ev["summary"]
    assert any("RCC" in c or "clock" in c for c in ev["possibleCauses"])


def test_decode_null_pointer_write():
    ev = crash.decode_fault(cfsr=0x00008200, bfar="0x00000000")
    assert any("null-pointer" in c for c in ev["possibleCauses"])


def test_decode_stack_overflow_hint():
    ev = crash.decode_fault(cfsr=0x00001000)  # STKERR
    assert any("stack overflow" in c for c in ev["possibleCauses"])


def test_decode_clean_registers_is_explicit():
    ev = crash.decode_fault(cfsr="0x00000000", hfsr="0x00000000", mmfar="0x00000000", bfar="0x00000000")
    assert ev["faults"] == ["no fault flags set (CFSR/HFSR clean)"]
    assert ev["possibleCauses"] == []


# ---------------------------------------------------------------- probe adapters

def test_probe_registry_lists_honest_statuses(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    listed = {p["id"]: p for p in probe_registry.list_probes()}
    assert listed["openocd"]["adapterStatus"] == "NOT_INSTALLED"
    assert listed["pyocd"]["adapterStatus"] == "NOT_SUPPORTED"
    assert listed["jlink"]["adapterStatus"] == "NOT_SUPPORTED"


def test_untested_adapter_refuses_hardware_actions(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    pyocd = probe_registry.get_probe("pyocd")
    flash = pyocd.flash("firmware.elf")
    assert flash["available"] is False and "never been tested" in flash["reason"]
    with pytest.raises(KeyError):
        probe_registry.get_probe("magic-probe")


def test_openocd_adapter_read_only_guards(monkeypatch):
    adapter = OpenOCDAdapter()
    refused = adapter.read_register("RCC_CR")  # cpu register allowlist only
    assert refused["available"] is False and "allowlist" in refused["reason"]
    mem_refused = adapter.read_memory32("MAGIC_ADDR")
    assert mem_refused["available"] is False
    write_refused = adapter.write_memory32("CFSR", 0)
    assert write_refused["available"] is False and "read-only" in write_refused["reason"]
    trace = adapter.collect_trace()
    assert trace["available"] is False


def test_openocd_adapter_parse_outputs(monkeypatch):
    adapter = OpenOCDAdapter()

    def fake_run(commands, timeout=20):
        if "mdw" in commands:
            output = "Info : stm32f1x.cpu: hardware has 6 breakpoints\n0xe000ed28: 00020000"
        elif "reg pc" in commands:
            output = "pc (/32): 0x0800014C"
        else:
            output = ""
        return {"available": True, "returncode": 0, "output": output}

    monkeypatch.setattr(adapter, "_run", fake_run)
    result = adapter.read_memory32("CFSR")
    assert result["available"] is True and result["value"] == "0x00020000"
    reg = adapter.read_register("pc")
    assert reg["value"] == "0x0800014C" and reg["status"] == "UNKNOWN"


# ---------------------------------------------------------------- debug workflow

class FakeProbe(DebugProbeAdapter):
    id = "fake"

    def __init__(self, flash_ok=True, regs=None, halt_ok=True):
        self.flash_ok = flash_ok
        self.regs = regs or {}
        self.halt_ok = halt_ok

    def detect(self):
        return {"available": True, "probeConnected": True}

    def identify_target(self):
        return {"available": True, "family": "STM32F1"}

    def flash(self, elf_path):
        if not self.flash_ok:
            return {"available": True, "status": "FAIL", "success": False, "reason": "flash failed"}
        return {"available": True, "status": "SUCCESS", "success": True, "exit_code": 0}

    def reset(self, mode="run"):
        return {"available": True, "status": "SUCCESS", "success": True}

    def halt(self):
        if not self.halt_ok:
            return {"available": True, "status": "FAIL", "halted": False, "reason": "halt failed"}
        return {"available": True, "status": "SUCCESS", "halted": True, "note": "halt dump only — not a PASS"}

    def resume(self):
        return {"available": True, "status": "SUCCESS"}

    def read_register(self, name):
        return {"available": True, "status": "UNKNOWN", "name": name, "value": self.regs.get(name)}

    def read_memory32(self, name):
        return {"available": True, "status": "UNKNOWN", "name": name, "value": self.regs.get(name.upper())}


def _mk_project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "Core/Src").mkdir(parents=True)
    (root / "Makefile").write_text("TARGET = firmware\n")
    return root


def test_workflow_build_failure_is_fail_and_stops(tmp_path, monkeypatch):
    root = _mk_project(tmp_path)
    monkeypatch.setattr(debug_workflow, "build_project_at", lambda r: {"status": "FAIL", "reason": "compile error"})
    result = debug_workflow.diagnose_no_output(root, probe=FakeProbe())
    assert result["status"] == "FAIL"
    assert result["steps"][0]["step"] == "build"
    assert result["crashEvidence"] is None


def test_workflow_flash_unavailable_is_honest(tmp_path, monkeypatch):
    root = _mk_project(tmp_path)
    monkeypatch.setattr(debug_workflow, "build_project_at", lambda r: {"status": "SUCCESS"})
    probe = FakeProbe()

    def flash(elf_path):
        return {"available": False, "status": "UNAVAILABLE", "success": False, "reason": "openocd not installed"}

    probe.flash = flash  # type: ignore[method-assign]
    result = debug_workflow.diagnose_no_output(root, probe=probe)
    assert result["status"] == "UNAVAILABLE"
    assert "openocd" in result["reason"]


def test_workflow_serial_output_prevents_overdiagnosis(tmp_path, monkeypatch):
    root = _mk_project(tmp_path)
    monkeypatch.setattr(debug_workflow, "build_project_at", lambda r: {"status": "SUCCESS"})
    result = debug_workflow.diagnose_no_output(
        root, probe=FakeProbe(), serial_wait=lambda s: ["CEA:USART:PASS"]
    )
    assert result["status"] == "PARTIAL"
    assert result["crashEvidence"] is None
    assert result["steps"][-1]["step"] == "serial"


def test_workflow_decodes_crash_from_registers(tmp_path, monkeypatch):
    root = _mk_project(tmp_path)
    monkeypatch.setattr(debug_workflow, "build_project_at", lambda r: {"status": "SUCCESS"})
    probe = FakeProbe(
        regs={
            "CFSR": "0x00020000",
            "HFSR": "0x40000000",
            "MMFAR": "0x00000000",
            "BFAR": "0x00000000",
            "PC": "0x08001234",
            "SP": "0x20001000",
        }
    )
    result = debug_workflow.diagnose_no_output(root, probe=probe, serial_wait=lambda s: [])
    ev = result["crashEvidence"]
    assert result["status"] == "PARTIAL"
    assert ev is not None
    assert any(f["name"] == "INVSTATE" for f in ev["flags"])
    assert ev["collectedBy"] == "fake"
    assert ev["note"].startswith("diagnosis from register evidence")


def test_workflow_without_probe_and_toolchain_unavailable(tmp_path, monkeypatch):
    root = _mk_project(tmp_path)
    monkeypatch.setattr(settings, "workspace_root", Path(tmp_path))
    # real default probe: openocd missing on this machine → flash step UNAVAILABLE
    monkeypatch.setattr(openocd_mod, "openocd_installed", lambda: False)
    result = debug_workflow.diagnose_no_output(root)
    assert result["status"] == "FAIL" or result["status"] == "UNAVAILABLE"
