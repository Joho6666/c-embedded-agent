from pathlib import Path

from app.tools.debug_read import dump_fault, read_register, read_symbol


def test_dump_fault_without_openocd_is_unavailable() -> None:
    out = dump_fault()
    assert out.get("status") != "PASS"
    assert out.get("status") in {"UNAVAILABLE", "UNKNOWN"} or out.get("available") in {False, True}


def test_read_register_reject_unknown() -> None:
    out = read_register("PC")
    assert out["available"] is False
    assert out["status"] == "UNAVAILABLE"


def test_read_symbol_missing_elf(tmp_path: Path) -> None:
    out = read_symbol(tmp_path, "main")
    assert out["status"] == "UNAVAILABLE"
    assert out.get("available") is False
