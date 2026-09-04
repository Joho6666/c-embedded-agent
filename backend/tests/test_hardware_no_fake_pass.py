from pathlib import Path

from app.tools.hardware_run import auto_debug, run_pipeline
from app.validation import hardware_status


def test_hardware_no_fake_pass(tmp_path: Path) -> None:
    (tmp_path / "Core" / "Src").mkdir(parents=True)
    (tmp_path / "Makefile").write_text("all:\n\t@echo skip\n", encoding="utf-8")
    result = run_pipeline(tmp_path, serial_device=None, task="usart")
    val = result.get("validation") or {}
    assert val.get("status") not in {"pass", "PASS"}
    assert val.get("status") in {"UNAVAILABLE", "UNKNOWN", "FAIL", "unknown", "fail", None} or val.get("status") != "PASS"


def test_auto_debug_without_openocd_does_not_claim_pass(tmp_path: Path) -> None:
    (tmp_path / "Core" / "Src").mkdir(parents=True)
    (tmp_path / "Makefile").write_text("all:\n\t@echo skip\n", encoding="utf-8")
    result = auto_debug(tmp_path, serial_device=None)
    val = result.get("validation") or {}
    assert val.get("status") not in {"pass", "PASS"}


def test_pwm_without_probe_is_partial() -> None:
    hw = hardware_status(serial_lines=None, expect=None, task="pwm", has_probe=False)
    assert hw["status"] in {"PARTIAL", "UNAVAILABLE"}
    assert hw["status"] != "PASS"


def test_usart_requires_token() -> None:
    hw = hardware_status(serial_lines=["hello world"], expect="CEA:USART:PASS", task="usart", has_probe=True)
    assert hw["status"] == "FAIL"
    hw2 = hardware_status(serial_lines=["CEA:USART:PASS"], expect="CEA:USART:PASS", task="usart", has_probe=True)
    assert hw2["status"] == "PASS"


def test_adc_value_range() -> None:
    bad = hardware_status(serial_lines=["CEA:ADC:value=99999"], expect=None, task="adc", has_probe=True)
    assert bad["status"] == "FAIL"
    good = hardware_status(serial_lines=["CEA:ADC:value=2048"], expect=None, task="adc", has_probe=True)
    assert good["status"] == "PASS"


def test_led_without_optical_probe_is_partial() -> None:
    hw = hardware_status(serial_lines=None, expect=None, task="led", has_probe=False)
    assert hw["status"] == "PARTIAL"
    assert "optical sensor" in hw["reason"]


def test_exti_requires_manual_button_step() -> None:
    hw = hardware_status(serial_lines=None, expect=None, task="exti", has_probe=False)
    assert hw["status"] == "MANUAL_STEP_REQUIRED"
    assert "manual user button press" in hw["reason"]


def test_usart_marker_stm32_pass() -> None:
    hw = hardware_status(serial_lines=["System booted", "CEA:STM32:PASS"], expect=None, task="usart", has_probe=True)
    assert hw["status"] == "PASS"
    assert hw["verdict"] == "VERIFIED_HARDWARE"


def test_hardware_run_saves_artifact(tmp_path: Path, monkeypatch) -> None:
    from app.config.settings import settings
    monkeypatch.setattr(settings, "repo_root", tmp_path)
    (tmp_path / "Core" / "Src").mkdir(parents=True)
    (tmp_path / "Makefile").write_text("all:\n\t@echo skip\n", encoding="utf-8")

    result = run_pipeline(tmp_path, serial_device=None, task="led")
    run_id = result.get("runId")
    assert run_id is not None
    run_dir = tmp_path / "runs" / run_id
    assert run_dir.is_dir()
    assert (run_dir / "metadata.json").is_file()
    assert (run_dir / "validation.json").is_file()
    assert (run_dir / "build.log").is_file()
