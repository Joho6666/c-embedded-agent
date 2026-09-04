from __future__ import annotations

from pathlib import Path
from app.release.gates import evaluate_release_candidate, check_hardware_evidence, check_backend_ci
from app.release.evidence import CapabilityStatus


def test_release_gates_reports_engineering_beta(tmp_path: Path) -> None:
    report = evaluate_release_candidate()
    assert report.version == "0.9.0-beta"
    assert report.is_production_candidate is False
    assert "NOT Production Candidate" in report.release_decision
    assert "hardware" in report.gates
    assert report.gates["hardware"].status in {"NOT_TESTED", "UNAVAILABLE"}


def test_hardware_gate_never_fake_pass() -> None:
    hw_gate = check_hardware_evidence(Path("."))
    assert hw_gate.status in {"NOT_TESTED", "UNAVAILABLE", "VERIFIED_HARDWARE"}
    if not hw_gate.details.get("probes"):
        assert hw_gate.passed is False
        assert hw_gate.status == "NOT_TESTED"


def test_backend_ci_gate_checks_pytest_asyncio() -> None:
    ci_gate = check_backend_ci(Path("."))
    assert ci_gate.passed is True
    assert ci_gate.status == "PASS"


def test_platform_capabilities_distinguish_verified_vs_implemented() -> None:
    report = evaluate_release_candidate()
    stm32 = report.capabilities["stm32f103-hal"]
    assert stm32.capabilities["build"].status == CapabilityStatus.VERIFIED_CI
    assert stm32.capabilities["hardware"].status == CapabilityStatus.NOT_TESTED
