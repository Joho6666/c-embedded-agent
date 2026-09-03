from pathlib import Path

from app.tools.hardware_run import auto_debug


def test_auto_debug_without_openocd_does_not_claim_pass(tmp_path: Path) -> None:
    (tmp_path / "Core" / "Src").mkdir(parents=True)
    (tmp_path / "Makefile").write_text("all:\n\t@echo skip\n", encoding="utf-8")
    result = auto_debug(tmp_path, serial_device=None)
    assert result["available"] is True
    statuses = {s["kind"]: s["status"] for s in result["steps"]}
    val = result.get("validation") or {}
    assert val.get("status") in {"unknown", "fail", None} or val.get("status") != "pass"
    if "flash" in statuses:
        assert statuses["flash"] != "success" or val.get("status") != "pass"
