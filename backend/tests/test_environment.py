from __future__ import annotations

from app.tools import detect


def test_environment_never_marks_missing_as_available(monkeypatch):
    monkeypatch.setattr(detect, "_which_any", lambda _names: None)
    monkeypatch.setattr(detect, "_run_version", lambda *_a, **_k: None)
    monkeypatch.setattr(detect, "_probe_windows_app", lambda *_a, **_k: None)
    monkeypatch.delenv("IDF_PATH", raising=False)

    payload = detect.environment_status()
    assert "items" in payload
    by_id = {item["id"]: item for item in payload["items"]}
    assert by_id["os"]["status"] == "available"
    for key in ("gcc", "clang", "arm-gcc", "cmake", "git", "cubemx", "openocd", "esp-idf", "sdcc", "keil"):
        assert by_id[key]["status"] in {"not_installed", "unknown", "not_configured"}
        assert by_id[key]["status"] != "available"


def test_environment_reports_found_tool(monkeypatch):
    monkeypatch.setattr(detect, "_which_any", lambda names: "/usr/bin/git" if "git" in names else None)
    monkeypatch.setattr(detect, "_run_version", lambda name, extra_args=None: "git version 2.0" if name == "git" else None)
    monkeypatch.setattr(detect, "_probe_windows_app", lambda *_a, **_k: None)
    monkeypatch.delenv("IDF_PATH", raising=False)
    payload = detect.environment_status()
    git = next(item for item in payload["items"] if item["id"] == "git")
    assert git["status"] == "available"
    assert git["version"]


def test_devices_cmsis_dap_is_not_detected(monkeypatch):
    monkeypatch.setattr(
        detect,
        "_probe_stlink",
        lambda: {"id": "stlink", "name": "st-info", "installed": False, "version": None, "connected": False},
    )
    monkeypatch.setattr("app.tools.serialutil.list_ports", lambda: [])
    payload = detect.connected_devices()
    cmsis = next(p for p in payload["probes"] if p["id"] == "cmsis-dap")
    stlink = next(p for p in payload["probes"] if p["id"] == "stlink")
    assert cmsis["presence"] == "not_detected"
    assert stlink["presence"] in {"not_detected", "unknown"}
    assert stlink["presence"] != "connected"


def test_stlink_connected_only_after_probe(monkeypatch):
    monkeypatch.setattr(
        detect,
        "_probe_stlink",
        lambda: {
            "id": "stlink",
            "name": "st-info",
            "installed": True,
            "version": "STM32F103 detected",
            "connected": True,
        },
    )
    monkeypatch.setattr("app.tools.serialutil.list_ports", lambda: [{"device": "COM5", "description": "USB Serial"}])
    payload = detect.connected_devices()
    stlink = next(p for p in payload["probes"] if p["id"] == "stlink")
    assert stlink["presence"] == "connected"
    assert payload["ports"][0]["presence"] == "available"
