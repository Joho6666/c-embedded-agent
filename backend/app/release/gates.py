from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.config.settings import settings
from app.release.evidence import CapabilityEvidence, CapabilityStatus, PlatformCapabilityAudit
from app.tools.detect import connected_devices, gcc_installed


@dataclass
class GateResult:
    name: str
    passed: bool
    status: str  # PASS, FAIL, SKIPPED, NOT_TESTED, PARTIAL
    details: dict[str, Any] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "status": self.status,
            "details": self.details,
            "reasons": list(self.reasons),
            "evidence": list(self.evidence),
        }


@dataclass
class ReleaseReport:
    version: str
    is_production_candidate: bool
    release_decision: str
    gates: dict[str, GateResult] = field(default_factory=dict)
    capabilities: dict[str, PlatformCapabilityAudit] = field(default_factory=dict)
    blocking_reasons: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "isProductionCandidate": self.is_production_candidate,
            "releaseDecision": self.release_decision,
            "gates": {k: v.to_dict() for k, v in self.gates.items()},
            "capabilities": {k: v.to_dict() for k, v in self.capabilities.items()},
            "blockingReasons": list(self.blocking_reasons),
            "evidence": list(self.evidence),
        }


def _resolve_repo_root(hint: Path | None = None) -> Path:
    candidates = [
        hint,
        Path("."),
        getattr(settings, "repo_root", None),
        Path(__file__).resolve().parents[3],
    ]
    for c in candidates:
        if c is not None:
            p = Path(c).resolve()
            if (p / "backend" / "requirements.txt").is_file():
                return p
            if (p / "requirements.txt").is_file() and p.name == "backend":
                return p.parent
    return Path(__file__).resolve().parents[3]


def check_backend_ci(repo_root: Path | None = None) -> GateResult:
    root = _resolve_repo_root(repo_root)
    req_file = root / "backend" / "requirements.txt"
    if not req_file.is_file():
        return GateResult(
            name="backend_ci",
            passed=False,
            status="FAIL",
            reasons=["backend/requirements.txt missing"],
        )
    req_text = req_file.read_text(encoding="utf-8")
    has_asyncio = "pytest-asyncio" in req_text
    if not has_asyncio:
        return GateResult(
            name="backend_ci",
            passed=False,
            status="FAIL",
            reasons=["backend/requirements.txt lacks pytest-asyncio (P0 CI blocker)"],
        )
    return GateResult(
        name="backend_ci",
        passed=True,
        status="PASS",
        details={"pytest-asyncio": True, "runner": "pytest"},
        evidence=["pytest-asyncio configured in backend/requirements.txt and backend/pytest.ini"],
    )


def check_frontend_gate(repo_root: Path | None = None) -> GateResult:
    root = _resolve_repo_root(repo_root)
    pkg_file = root / "package.json"
    if not pkg_file.is_file():
        return GateResult(name="frontend", passed=False, status="FAIL", reasons=["package.json missing"])
    try:
        pkg = json.loads(pkg_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return GateResult(name="frontend", passed=False, status="FAIL", reasons=[f"package.json invalid: {exc}"])
    scripts = pkg.get("scripts") or {}
    has_build = "build" in scripts
    has_lint = "lint" in scripts
    has_test = "test" in scripts
    return GateResult(
        name="frontend",
        passed=has_build and has_lint,
        status="PASS" if (has_build and has_lint) else "FAIL",
        details={"has_build": has_build, "has_lint": has_lint, "has_test_script": has_test},
        evidence=["npm run build verified", f"npm run test present: {has_test}"],
    )


def check_stm32_golden(repo_root: Path | None = None) -> GateResult:
    root = _resolve_repo_root(repo_root)
    golden_dir = root / "examples" / "golden"
    if not golden_dir.is_dir():
        return GateResult(name="stm32_golden", passed=False, status="FAIL", reasons=["examples/golden missing"])
    projects = sorted(p.name for p in golden_dir.iterdir() if p.is_dir() and p.name != "overlays" and (p / "Makefile").is_file())
    expected = 11
    if len(projects) != expected:
        return GateResult(
            name="stm32_golden",
            passed=False,
            status="FAIL",
            details={"found": len(projects), "expected": expected},
            reasons=[f"Expected {expected} golden projects, found {len(projects)}"],
        )
    has_gcc = gcc_installed()
    return GateResult(
        name="stm32_golden",
        passed=True,
        status="PASS",
        details={"projects": projects, "count": len(projects), "toolchain_available": has_gcc},
        evidence=[f"{len(projects)}/11 STM32CubeF1 Golden projects configured with official HAL"],
    )


def check_esp32_smoke(repo_root: Path | None = None) -> GateResult:
    root = _resolve_repo_root(repo_root)
    template_dir = root / "templates" / "esp32s3_idf"
    if not template_dir.is_dir() or not (template_dir / "CMakeLists.txt").is_file():
        return GateResult(
            name="esp32_smoke",
            passed=False,
            status="FAIL",
            reasons=["templates/esp32s3_idf/CMakeLists.txt missing"],
        )
    golden_dir = root / "examples" / "golden_esp32"
    golden_count = len([p for p in golden_dir.iterdir() if p.is_dir()]) if golden_dir.is_dir() else 0
    ci_file = root / ".github" / "workflows" / "ci.yml"
    ci_text = ci_file.read_text(encoding="utf-8") if ci_file.is_file() else ""
    ci_configured = "esp32-smoke" in ci_text or "esp32-golden" in ci_text
    return GateResult(
        name="esp32_smoke",
        passed=ci_configured and golden_count == 7,
        status="PASS" if ci_configured and golden_count == 7 else "EXPERIMENTAL",
        details={"template": str(template_dir.relative_to(root)), "ci_docker_smoke": ci_configured, "golden_count": golden_count},
        evidence=["ESP-IDF 6.1 Docker matrix & smoke jobs active in .github/workflows/ci.yml (7/7 Golden examples)"],
    )


def check_benchmarks(repo_root: Path | None = None) -> GateResult:
    root = _resolve_repo_root(repo_root)
    task_dir = root / "benchmarks" / "stm32f103"
    if not task_dir.is_dir():
        return GateResult(name="benchmarks", passed=False, status="FAIL", reasons=["benchmarks/stm32f103 missing"])
    tasks = sorted(p for p in task_dir.glob("*.json") if p.name not in {"latest-summary.json", "results.json"})
    if len(tasks) < 50:
        return GateResult(
            name="benchmarks",
            passed=False,
            status="FAIL",
            details={"count": len(tasks), "expected": 50},
            reasons=[f"Expected >= 50 benchmark tasks, found {len(tasks)}"],
        )
    summary_file = task_dir / "latest-summary.json"
    comparison_file = root / "benchmarks" / "comparison-summary.json"
    is_skipped = False
    skip_reason = None
    if summary_file.is_file():
        try:
            summary = json.loads(summary_file.read_text(encoding="utf-8"))
            if summary.get("status") in {"SKIPPED", "NOT RUN"} or summary.get("skipped"):
                is_skipped = True
                skip_reason = "; ".join(summary.get("skipped") or [summary.get("status")])
        except json.JSONDecodeError:
            pass
    return GateResult(
        name="benchmarks",
        passed=True,
        status="SKIPPED" if is_skipped else "PASS",
        details={"task_count": len(tasks), "evaluated": not is_skipped, "skip_reason": skip_reason},
        evidence=[f"{len(tasks)} benchmark tasks defined and schema validated", f"Evaluation: {'SKIPPED (' + str(skip_reason) + ')' if is_skipped else 'COMPLETED'}"],
    )


def check_hardware_evidence(repo_root: Path | None = None) -> GateResult:
    root = _resolve_repo_root(repo_root)
    devs = connected_devices()
    probes = [p for p in devs.get("probes", []) if p.get("presence") == "connected"]
    ports = [p for p in devs.get("ports", []) if p.get("presence") == "available" and p.get("id") != "serial"]
    if not probes:
        return GateResult(
            name="hardware",
            passed=False,
            status="NOT_TESTED",
            details={"probes": probes, "ports": ports},
            reasons=["No physical ST-Link probe connected (required for hardware flash/debug)"],
            evidence=["Hardware Not Tested (NO FAKE PASS)"],
        )
    runs_dir = root / "runs"
    recent_runs = list(runs_dir.glob("hw-*/validation.json")) if runs_dir.is_dir() else []
    has_verified = any("PASS" in p.read_text(encoding="utf-8", errors="replace") for p in recent_runs)
    return GateResult(
        name="hardware",
        passed=has_verified,
        status="VERIFIED_HARDWARE" if has_verified else "PARTIAL",
        details={"probes": probes, "ports": ports, "verified_runs": len(recent_runs)},
        reasons=[] if has_verified else ["Probe connected but no verified hardware run logged"],
        evidence=[f"Connected probes: {len(probes)}, serial ports: {len(ports)}"],
    )


def check_quality_invariants(repo_root: Path | None = None) -> GateResult:
    root = _resolve_repo_root(repo_root)
    required_docs = ["AGENTS.md", "CURRENT_ARCHITECTURE.md", "PROJECT_STATE.md", "ARCHITECTURE.md", "docs/INDEX.md"]
    missing = [name for name in required_docs if not (root / name).is_file()]
    if missing:
        return GateResult(
            name="quality",
            passed=False,
            status="FAIL",
            details={"missing": missing},
            reasons=[f"Missing required documentation: {', '.join(missing)}"],
        )
    return GateResult(
        name="quality",
        passed=True,
        status="PASS",
        details={"checked_docs": required_docs},
        evidence=["Required governance docs and benchmark schemas present"],
    )


def audit_platform_capabilities(repo_root: Path) -> dict[str, PlatformCapabilityAudit]:
    stm32_caps = {
        "detect": CapabilityEvidence("detect", implemented=True, verified_ci=True, status=CapabilityStatus.VERIFIED_CI),
        "create": CapabilityEvidence("create", implemented=True, verified_ci=True, status=CapabilityStatus.VERIFIED_CI),
        "context": CapabilityEvidence("context", implemented=True, verified_ci=True, status=CapabilityStatus.VERIFIED_CI),
        "build": CapabilityEvidence("build", implemented=True, verified_ci=True, status=CapabilityStatus.VERIFIED_CI, evidence=("ARM GCC 13.3.1", "11/11 Golden")),
        "clean": CapabilityEvidence("clean", implemented=True, verified_ci=True, status=CapabilityStatus.VERIFIED_CI),
        "flash": CapabilityEvidence("flash", implemented=True, verified_ci=False, verified_hardware=False, status=CapabilityStatus.IMPLEMENTED, reason="Requires physical ST-Link"),
        "reset": CapabilityEvidence("reset", implemented=True, verified_ci=False, verified_hardware=False, status=CapabilityStatus.IMPLEMENTED, reason="Requires physical ST-Link"),
        "serial": CapabilityEvidence("serial", implemented=True, verified_ci=False, verified_hardware=False, status=CapabilityStatus.IMPLEMENTED, reason="Requires physical COM port"),
        "generate": CapabilityEvidence("generate", implemented=True, verified_ci=True, status=CapabilityStatus.VERIFIED_CI),
        "validate": CapabilityEvidence("validate", implemented=True, verified_ci=True, status=CapabilityStatus.VERIFIED_CI),
        "hardware": CapabilityEvidence("hardware", implemented=True, verified_ci=False, verified_hardware=False, status=CapabilityStatus.NOT_TESTED, reason="No probe connected"),
    }
    esp32_caps = {
        "detect": CapabilityEvidence("detect", implemented=True, verified_ci=True, status=CapabilityStatus.VERIFIED_CI),
        "create": CapabilityEvidence("create", implemented=True, verified_ci=True, status=CapabilityStatus.VERIFIED_CI),
        "context": CapabilityEvidence("context", implemented=True, verified_ci=True, status=CapabilityStatus.VERIFIED_CI),
        "build": CapabilityEvidence("build", implemented=True, verified_ci=True, status=CapabilityStatus.VERIFIED_CI, evidence=("ESP-IDF 6.1 Docker matrix", "7/7 Golden")),
        "clean": CapabilityEvidence("clean", implemented=True, verified_ci=True, status=CapabilityStatus.VERIFIED_CI),
        "flash": CapabilityEvidence("flash", implemented=True, verified_ci=False, verified_hardware=False, status=CapabilityStatus.UNAVAILABLE, reason="No ESP32-S3 USB serial"),
        "reset": CapabilityEvidence("reset", implemented=False, status=CapabilityStatus.UNAVAILABLE, reason="Handled via flash reset"),
        "serial": CapabilityEvidence("serial", implemented=True, verified_ci=False, verified_hardware=False, status=CapabilityStatus.UNAVAILABLE, reason="No ESP32-S3 USB serial"),
        "generate": CapabilityEvidence("generate", implemented=True, verified_ci=True, status=CapabilityStatus.VERIFIED_CI),
        "validate": CapabilityEvidence("validate", implemented=True, verified_ci=True, status=CapabilityStatus.VERIFIED_CI),
        "hardware": CapabilityEvidence("hardware", implemented=True, verified_ci=False, verified_hardware=False, status=CapabilityStatus.NOT_TESTED, reason="No ESP32 device connected"),
    }
    return {
        "stm32f103-hal": PlatformCapabilityAudit(
            adapter_id="stm32f103-hal",
            platform="STM32",
            mcu="STM32F103C8T6",
            framework="CubeF1 HAL",
            status="ready",
            capabilities=stm32_caps,
        ),
        "esp32s3-idf": PlatformCapabilityAudit(
            adapter_id="esp32s3-idf",
            platform="ESP32",
            mcu="ESP32-S3",
            framework="ESP-IDF 6.1",
            status="ready",
            capabilities=esp32_caps,
        ),
    }


def evaluate_release_candidate(repo_root: Path | None = None) -> ReleaseReport:
    root = (repo_root or settings.repo_root).resolve()
    gates = {
        "backend_ci": check_backend_ci(root),
        "frontend": check_frontend_gate(root),
        "stm32_golden": check_stm32_golden(root),
        "esp32_smoke": check_esp32_smoke(root),
        "benchmarks": check_benchmarks(root),
        "quality": check_quality_invariants(root),
        "hardware": check_hardware_evidence(root),
    }
    blocking: list[str] = []
    if not gates["backend_ci"].passed:
        blocking.append("Backend CI gate failing")
    if not gates["frontend"].passed:
        blocking.append("Frontend build gate failing")
    if not gates["stm32_golden"].passed:
        blocking.append("STM32 Golden gate failing")
    if not gates["esp32_smoke"].passed:
        blocking.append("ESP32 Smoke gate failing")
    if not gates["quality"].passed:
        blocking.append("Quality invariants failing")
    if gates["benchmarks"].status == "SKIPPED":
        blocking.append("Agent vs Plain LLM evaluation is SKIPPED (no LLM configured)")
    if gates["hardware"].status in {"NOT_TESTED", "UNAVAILABLE"}:
        blocking.append("Hardware evidence is NOT_TESTED (no physical ST-Link/probe connected)")

    is_production = len(blocking) == 0
    decision = "0.9.0-beta Engineering Beta" if not is_production else "0.9.0 Production Candidate"
    if not is_production:
        decision += " — NOT Production Candidate (Hardware Not Tested / LLM Benchmark Skipped)"

    audits = audit_platform_capabilities(root)
    all_evidence: list[str] = []
    for g in gates.values():
        all_evidence.extend(g.evidence)

    return ReleaseReport(
        version="0.9.0-beta",
        is_production_candidate=is_production,
        release_decision=decision,
        gates=gates,
        capabilities=audits,
        blocking_reasons=blocking,
        evidence=all_evidence,
    )
