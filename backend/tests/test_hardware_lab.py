"""Hardware Lab tests — device model, discovery, map, HardwareRun honesty."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config.settings import settings
from app.hardware import devices as device_store
from app.hardware import discovery
from app.hardware.hardware_map import check_required_devices, load_hardware_map, parse_hardware_map
from app.hardware.models import DeviceError, normalize_device
from app.hardware import session as hw_session
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------- models

def test_normalize_device_fills_defaults():
    d = normalize_device({"id": "dev-1"})
    assert d["mcu"] == "UNKNOWN"
    assert d["status"] == "UNKNOWN"
    assert d["capabilities"] == []
    assert d["source"] == "manual"


def test_normalize_device_rejects_missing_id_and_bad_status():
    with pytest.raises(DeviceError):
        normalize_device({"board": "Blue Pill"})
    with pytest.raises(DeviceError):
        normalize_device({"id": "x", "status": "CONNECTED"})


def test_normalize_device_blocks_usb_hint_mcu_claims():
    with pytest.raises(DeviceError):
        normalize_device({"id": "x", "mcu": "STM32F103C8T6", "mcuEvidence": "usb-hint"})
    ok = normalize_device({"id": "x", "mcu": "STM32F103C8T6", "mcuEvidence": "manual"})
    assert ok["mcu"] == "STM32F103C8T6"


# ---------------------------------------------------------------- discovery

def _fake_stlink(connected: bool = True):
    if connected:
        return {"id": "stlink", "installed": True, "connected": True, "version": "ST-LINK/V2", "detail": None}
    return {"id": "stlink", "installed": True, "connected": False, "version": None, "detail": "Not Detected"}


def test_usb_table_maps_known_devices():
    ports = discovery._decode_serial_ports(
        lambda: [
            {"device": "COM7", "description": "USB-SERIAL CH340", "hwid": "USB VID:PID=1A86:7523 SER=ABC LOCATION=1-1.3"},
            {"device": "COM9", "description": "ST-Link Debug", "hwid": "USB VID:PID=0483:3748 SER=DEF"},
            {"device": "COM11", "description": "Unknown", "hwid": "USB VID:PID=1234:5678"},
        ]
    )
    ch340 = next(p for p in ports if p["device"] == "COM7")
    stlink = next(p for p in ports if p["device"] == "COM9")
    unknown = next(p for p in ports if p["device"] == "COM11")
    assert (ch340["usbName"], ch340["kind"]) == ("CH340", "usb-serial")
    assert (stlink["usbName"], stlink["kind"]) == ("ST-LINK/V2", "debug-probe")
    assert unknown["kind"] is None and unknown["vid"] == "1234"


def test_discovery_report_keeps_mcu_unknown(monkeypatch):
    monkeypatch.setattr(discovery, "stlink_probe", lambda: _fake_stlink(True))
    ports_fn = lambda: [  # noqa: E731
        {"device": "COM7", "description": "USB-SERIAL CH340", "hwid": "USB VID:PID=1A86:7523 SER=ABC"}
    ]
    report = discovery.discover(list_ports_fn=ports_fn)
    ids = {d["id"] for d in report["devices"]}
    assert "probe-stlink" in ids and "serial-com7" in ids
    for d in report["devices"]:
        assert d["mcu"] == "UNKNOWN"
        assert d["mcuEvidence"] is None
    assert report["exactMcu"] == "UNKNOWN"
    assert any("chip-id" in s for s in report["nextSteps"])


def test_discovery_without_probe_is_honest(monkeypatch):
    monkeypatch.setattr(discovery, "stlink_probe", lambda: _fake_stlink(False))
    report = discovery.discover(list_ports_fn=lambda: [])
    st = next(p for p in report["probes"] if p["id"] == "stlink")
    assert st["presence"] == "not_detected"  # installed but not connected
    assert all(d["id"] != "probe-stlink" for d in report["devices"])


def test_identify_target_reports_missing_openocd(monkeypatch):
    from app.tools import flash

    monkeypatch.setattr(flash, "detect_chip_id", lambda: {"available": False, "id": None, "family": None})
    result = discovery.identify_target()
    assert result["available"] is False
    assert "OpenOCD" in result["reason"]


# ---------------------------------------------------------------- device store

@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "workspace_root", str(tmp_path))
    return tmp_path


def test_device_store_crud(workspace: Path):
    device_store.upsert_device({"id": "probe-stlink", "debugProbe": "ST-Link"})
    device_store.upsert_device({"id": "probe-stlink", "debugProbe": "ST-Link", "serialPort": "COM7"})
    stored = device_store.load_devices()
    assert len(stored) == 1 and stored[0]["serialPort"] == "COM7"
    assert device_store.delete_device("probe-stlink") is True
    assert device_store.delete_device("probe-stlink") is False
    assert device_store.load_devices() == []


def test_refresh_from_discovery_marks_absent_offline(workspace: Path):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    device_store.upsert_device({"id": "probe-stlink", "source": "discovery", "status": "ONLINE", "lastSeenAt": now})
    empty_report = {"devices": [normalize_device({"id": "serial-com9", "source": "discovery", "status": "ONLINE"})]}
    out = {d["id"]: d for d in device_store.refresh_from_discovery(empty_report)}
    assert out["probe-stlink"]["status"] == "OFFLINE"
    assert out["serial-com9"]["status"] == "ONLINE"


# ---------------------------------------------------------------- hardware map

SAMPLE_MAP = """
# lab inventory
defaults:
  baud: 115200
devices:
  - id: bluepill-01
    platform: stm32
    board: Blue Pill
    mcu: STM32F103C8T6
    probe: ST-Link
    probeSerial: "0668FF3833"
    serial: COM7
    capabilities: [flash, serial, gpio-probe]
    tags: [golden]
  - id: bluepill-02
    platform: stm32
    board: Blue Pill
    capabilities: [flash]
"""


def test_hardware_map_parser():
    parsed = parse_hardware_map(SAMPLE_MAP)
    assert parsed["defaults"] == {"baud": 115200}
    assert len(parsed["devices"]) == 2
    first = parsed["devices"][0]
    assert first["id"] == "bluepill-01"
    assert first["mcu"] == "STM32F103C8T6"
    assert first["probeSerial"] == "0668FF3833"
    assert first["capabilities"] == ["flash", "serial", "gpio-probe"]
    assert parsed["devices"][1].get("mcu") is None


def test_hardware_map_load_missing_is_honest(tmp_path: Path):
    parsed = load_hardware_map(tmp_path / "no-such-map.yaml")
    assert parsed["available"] is False and parsed["devices"] == []


def test_check_required_devices(workspace: Path, tmp_path: Path):
    map_path = workspace / "hardware-map.yaml"
    map_path.write_text(SAMPLE_MAP, encoding="utf-8")
    map_data = load_hardware_map(map_path)
    registry = [
        {"id": "bluepill-01", "status": "ONLINE"},
        {"id": "bluepill-02", "status": "OFFLINE"},
    ]
    check = check_required_devices(1, map_data, registry)
    assert check["satisfied"] is True and check["online"] == ["bluepill-01"]
    check2 = check_required_devices(2, map_data, registry)
    assert check2["satisfied"] is False and check2["missing"] == 1


# ---------------------------------------------------------------- HardwareRun

def _mk_run(tmp_path: Path) -> dict:
    (tmp_path / "firmware.bin").write_bytes(b"\x00\x01\x02")
    (tmp_path / "firmware.elf").write_bytes(b"ELF")
    return hw_session.create_run(tmp_path, session={"board": "Blue Pill", "mcu": "UNKNOWN", "baud": 115200})


def test_hardware_run_hashes_and_defaults(tmp_path: Path):
    run = _mk_run(tmp_path)
    assert run["firmwareHash"] and run["elfHash"]
    assert run["status"] == "UNKNOWN" and run["serialDevice"] is None
    assert run["board"] == "Blue Pill"


def test_hardware_run_pass_gate_requires_hardware_evidence(tmp_path: Path):
    run = _mk_run(tmp_path)
    hw_session.finalize_run(run, "FAIL")  # honest FAIL is always allowed
    assert run["status"] == "FAIL"

    run2 = _mk_run(tmp_path)
    hw_session.set_flash_result(run2, "openocd -c program", {"success": True, "exit_code": 0, "output": "ok"})
    with pytest.raises(hw_session.HardwareRunError):
        hw_session.finalize_run(run2, "PASS")  # flash alone is not hardware evidence

    hw_session.add_evidence(
        run2, "HARDWARE", {"claim": "CEA:USART:PASS token received", "passed": True}
    )
    hw_session.finalize_run(run2, "PASS")
    assert run2["status"] == "PASS" and run2["finishedAt"]


def test_hardware_run_rejects_invalid_status(tmp_path: Path):
    run = _mk_run(tmp_path)
    with pytest.raises(hw_session.HardwareRunError):
        hw_session.finalize_run(run, "UNVERIFIED")  # not in the closed vocabulary
    with pytest.raises(hw_session.HardwareRunError):
        hw_session.add_evidence(run, "TELEPATHY", {"passed": True})


def test_hardware_run_save_load_roundtrip(tmp_path: Path):
    run = _mk_run(tmp_path)
    hw_session.set_flash_result(run, "cmd", {"success": False, "exit_code": 1, "output": "no probe"})
    hw_session.finalize_run(run, "UNAVAILABLE")
    path = hw_session.save_run(tmp_path, run)
    assert path.is_file()
    loaded = hw_session.load_run(tmp_path, run["runId"])
    assert loaded["status"] == "UNAVAILABLE"
    assert (tmp_path / "hardware-runs" / "latest.json").is_file()
    assert len(hw_session.load_runs(tmp_path)) == 1


# ---------------------------------------------------------------- API wiring

def test_api_hardware_device_endpoints(workspace: Path):
    r = client.get("/api/hardware/devices")
    assert r.status_code == 200 and r.json() == []
    r = client.post("/api/hardware/devices", json={"id": "dev-x", "debugProbe": "ST-Link"})
    assert r.status_code == 200 and r.json()["id"] == "dev-x"
    assert len(client.get("/api/hardware/devices").json()) == 1
    assert client.delete("/api/hardware/devices/dev-x").status_code == 200
    assert client.delete("/api/hardware/devices/dev-x").status_code == 404


def test_api_discovery_report_endpoint(workspace: Path, monkeypatch):
    monkeypatch.setattr(discovery, "stlink_probe", lambda: _fake_stlink(False))
    monkeypatch.setattr("app.main.hardware_discover", lambda: discovery.discover(list_ports_fn=lambda: []))
    r = client.post("/api/hardware/discovery")
    assert r.status_code == 200
    body = r.json()
    assert body["exactMcu"] == "UNKNOWN"
    cached = client.get("/api/hardware/discovery-report")
    assert cached.status_code == 200 and cached.json()["generatedAt"] == body["generatedAt"]


def test_api_hardware_map_endpoint(workspace: Path):
    (Path(settings.workspace_root) / "hardware-map.yaml").write_text(SAMPLE_MAP, encoding="utf-8")
    r = client.get("/api/hardware/map")
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True and len(body["devices"]) == 2
