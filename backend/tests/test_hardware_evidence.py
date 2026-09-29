"""Phase E tests: evidence model, peripheral requirements, safety, human loop."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config.settings import settings
from app.hardware import evidence as ev
from app.hardware import human_loop
from app.hardware import peripheral_evidence as pe
from app.hardware import safety


# ---------------------------------------------------------------- evidence

def test_make_evidence_rejects_bad_level():
    with pytest.raises(ev.EvidenceError):
        ev.make_evidence("claim", level="VIBES")


def test_make_evidence_hashes_artifact(tmp_path: Path):
    art = tmp_path / "firmware.bin"
    art.write_bytes(b"abc")
    rec = ev.make_evidence("built", level="BUILD", passed=True, artifact=art)
    assert len(rec["artifactHash"]) == 64
    assert rec["passed"] is True


def test_report_levels_stay_separate():
    records = [
        ev.make_evidence("compiled", level="BUILD", passed=True),
        ev.make_evidence("flash ok", level="HARDWARE", passed=False),
    ]
    report = ev.verification_report(records)
    assert report["levels"] == {"BUILD": "PASS", "SIMULATION": "NOT_TESTED", "HARDWARE": "FAIL"}
    assert report["overall"] == "FAIL"


def test_report_partial_when_hardware_not_tested():
    records = [ev.make_evidence("compiled", level="BUILD", passed=True)]
    report = ev.verification_report(records)
    assert report["levels"]["HARDWARE"] == "NOT_TESTED"
    assert report["overall"] == "PARTIAL"  # the headline honesty rule


def test_report_not_tested_when_nothing_ran():
    assert ev.verification_report([])["overall"] == "NOT_TESTED"


def test_report_full_pass_only_with_all_levels():
    records = [
        ev.make_evidence("compiled", level="BUILD", passed=True),
        ev.make_evidence("simulated", level="SIMULATION", passed=True),
        ev.make_evidence("flashed+validated", level="HARDWARE", passed=True),
    ]
    assert ev.verification_report(records)["overall"] == "PASS"


def test_report_pass_survives_missing_simulation():
    """Hardware+Build PASS with no simulation layer available stays PASS —
    an absent simulator must not fake or block hardware results."""
    records = [
        ev.make_evidence("compiled", level="BUILD", passed=True),
        ev.make_evidence("flashed+validated", level="HARDWARE", passed=True),
    ]
    report = ev.verification_report(records)
    assert report["overall"] == "PASS" and report["levels"]["SIMULATION"] == "NOT_TESTED"


def test_report_sim_pass_hardware_untested_is_partial():
    records = [
        ev.make_evidence("compiled", level="BUILD", passed=True),
        ev.make_evidence("simulated", level="SIMULATION", passed=True),
    ]
    assert ev.verification_report(records)["overall"] == "PARTIAL"


def test_report_from_hardware_run_roundtrip():
    run = {
        "toolchain": "arm-none-eabi-gcc",
        "firmwareHash": "ab" * 32,
        "flashResult": {"success": True, "at": "t1"},
        "serialLog": ["CEA:USART:PASS"],
        "hardwareEvidence": [{"level": "HARDWARE", "claim": "token", "passed": True, "at": "t2"}],
        "debugEvidence": [],
        "startedAt": "t0",
        "finishedAt": "t3",
    }
    records = ev.evidence_from_hardware_run(run)
    report = ev.verification_report(records)
    assert report["levels"]["BUILD"] == "PASS"
    assert report["levels"]["HARDWARE"] == "PASS"
    assert report["overall"] == "PASS"


# ---------------------------------------------------------------- peripheral evidence

def test_usart_requires_real_token():
    empty = pe.evaluate_peripheral("usart", [])
    assert empty["status"] == "NOT_TESTED"
    code_only = pe.evaluate_peripheral("usart", [ev.make_evidence("calls HAL_UART_Transmit", level="BUILD", passed=True, method="static-inspection")])
    assert code_only["status"] == "NOT_TESTED"  # code inspection is not evidence
    ok = pe.evaluate_peripheral(
        "usart", [ev.make_evidence("CEA:USART:PASS received", level="HARDWARE", passed=True, method="serial-token")]
    )
    assert ok["status"] == "PASS"


def test_led_needs_observed_toggle():
    compile_only = pe.evaluate_peripheral(
        "led", [ev.make_evidence("main.c toggles PC13", level="BUILD", passed=True, method="static-inspection")]
    )
    assert compile_only["status"] == "NOT_TESTED"
    observed = pe.evaluate_peripheral(
        "led", [ev.make_evidence("PC13 seen toggling", level="HARDWARE", passed=True, method="debugger-register")]
    )
    assert observed["status"] == "PASS"


def test_gpio_input_rejects_hal_readpin_only():
    res = pe.evaluate_peripheral(
        "gpio_input", [ev.make_evidence("code calls HAL_GPIO_ReadPin", level="BUILD", passed=True, method="static-inspection")]
    )
    assert res["status"] == "NOT_TESTED"
    assert "proves nothing" in res["note"]


def test_pwm_register_evidence_is_partial_quality():
    la = pe.evaluate_peripheral(
        "pwm", [ev.make_evidence("1kHz 50% measured", level="HARDWARE", passed=True, method="logic-analyzer")]
    )
    assert la["status"] == "PASS"
    reg = pe.evaluate_peripheral(
        "pwm", [ev.make_evidence("TIM2_CNT increments", level="HARDWARE", passed=True, method="debugger-register")]
    )
    assert reg["status"] == "PASS"  # register sampling is an accepted method


def test_contradicting_evidence_fails():
    res = pe.evaluate_peripheral(
        "usart",
        [
            ev.make_evidence("no output seen", level="HARDWARE", passed=False, method="serial-token"),
            ev.make_evidence("token", level="HARDWARE", passed=True, method="serial-token"),
        ],
    )
    assert res["status"] == "FAIL"


def test_unknown_peripheral_honest():
    assert pe.evaluate_peripheral("can", [])["status"] == "NOT_TESTED"


# ---------------------------------------------------------------- safety

def test_dangerous_operations_blocked_by_default():
    for op in ("mass_erase", "option_bytes_write", "bootloader_overwrite"):
        gate = safety.check_operation(op)
        assert gate["allowed"] is False and gate["level"] == "DANGEROUS_HARDWARE"


def test_dangerous_operation_requires_and_consumes_token():
    with pytest.raises(ValueError):
        safety.approve_operation("mass_erase", "x")  # too short
    safety.approve_operation("mass_erase", "human-said-yes-123")
    gate = safety.check_operation("mass_erase", token="human-said-yes-123")
    assert gate["allowed"] is True
    # single use
    gate2 = safety.check_operation("mass_erase", token="human-said-yes-123")
    assert gate2["allowed"] is False
    safety.revoke_all()


def test_unknown_operation_rejected():
    assert safety.check_operation("teleport_board")["allowed"] is False


def test_power_controller_is_interface_only():
    pc = safety.PowerControllerAdapter()
    assert pc.power_on()["available"] is False
    assert pc.power_cycle()["status"] == "UNAVAILABLE"


# ---------------------------------------------------------------- human loop

def test_user_action_wait_confirm_cycle(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "workspace_root", Path(tmp_path))
    req = human_loop.request_user_action("按下 Blue Pill 上的 BOOT0 跳线并复位", project_id="p1")
    assert req["status"] == "WAITING_FOR_USER"
    assert human_loop.pending_actions("p1")[0]["id"] == req["id"]
    confirmed = human_loop.confirm_user_action(req["id"], "confirmed")
    assert confirmed["status"] == "CONFIRMED" and confirmed["resolvedAt"]
    assert human_loop.pending_actions("p1") == []
    with pytest.raises(ValueError):
        human_loop.confirm_user_action(req["id"])  # already resolved


def test_user_action_requires_description(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "workspace_root", Path(tmp_path))
    with pytest.raises(ValueError):
        human_loop.request_user_action("  ")
