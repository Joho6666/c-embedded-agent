from __future__ import annotations

from dataclasses import asdict, dataclass
import shutil
from typing import Any

from app.agent.approvals import ApprovalPolicyManager, ToolRiskLevel
from app.agent.task_classifier import ContextLevel, TaskClassifier
from app.agent.workflow_router import CoreWorkflow, WorkflowRouter
from app.tools.detect import connected_devices, gcc_installed
from app.tools.registry import default_tool_registry


@dataclass(frozen=True)
class PlannedStep:
    id: str
    tool: str
    reason: str
    expected_evidence: str | list[str]
    preconditions: tuple[str, ...] = ()
    resume_policy: str = "replay"
    requires_approval: bool = False

    def to_dict(self) -> dict[str, Any]:
        ev_list = [self.expected_evidence] if isinstance(self.expected_evidence, str) else list(self.expected_evidence)
        return {
            "id": self.id,
            "tool": self.tool,
            "reason": self.reason,
            "preconditions": list(self.preconditions),
            "expectedEvidence": ev_list,
            "expected_evidence": "; ".join(ev_list) if isinstance(self.expected_evidence, (list, tuple)) else self.expected_evidence,
            "resumePolicy": self.resume_policy,
            "requiresApproval": self.requires_approval,
        }


@dataclass(frozen=True)
class ActionPlan:
    goal: str
    platform: str
    workflow: str
    steps: tuple[PlannedStep, ...]
    risk: str
    requires_approval: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "platform": self.platform,
            "workflow": self.workflow,
            "risk": self.risk,
            "requires_approval": self.requires_approval,
            "requiresApproval": self.requires_approval,
            "steps": [s.to_dict() for s in self.steps],
        }


def make_plan(prompt: str) -> list[dict[str, Any]]:
    steps = list(WorkflowRouter().route(prompt).steps)
    return [{"id": f"s{i+1}", "index": i + 1, "title": t, "status": "pending"} for i, t in enumerate(steps)]


def looks_complex(prompt: str) -> bool:
    return TaskClassifier().classify(prompt).context_level is not ContextLevel.FOCUSED


def generate_action_plan(
    prompt: str,
    *,
    platform: str | None = None,
    context: dict[str, Any] | None = None,
) -> ActionPlan:
    """Generate a rigorous, structured ActionPlan knowing platform, available tools, device status, and risk."""
    classifier = TaskClassifier()
    classification = classifier.classify(prompt, platform=platform)
    target_platform = classification.platform or platform or "STM32"
    router = WorkflowRouter(classifier)
    wf = router.route(prompt, classification)

    registry = default_tool_registry()
    available_tools = {spec.name for spec in registry.list(available_only=False)}

    # Inspect device status to avoid planning unavailable capabilities as PASS
    devs = connected_devices()
    probes = [p for p in devs.get("probes", []) if p.get("presence") == "connected"]
    ports = [p for p in devs.get("ports", []) if p.get("presence") == "available" and p.get("id") != "serial"]
    has_probe = len(probes) > 0
    has_port = len(ports) > 0

    # Inspect toolchains
    if target_platform.lower().startswith("stm32"):
        toolchain_ok = gcc_installed()
    elif target_platform.lower().startswith("esp32"):
        toolchain_ok = shutil.which("idf.py") is not None
    elif "8051" in target_platform.lower():
        toolchain_ok = shutil.which("sdcc") is not None
    else:
        toolchain_ok = False

    raw_steps: list[tuple[str, str, list[str], tuple[str, ...]]] = []

    # 1. Understanding & Context step
    raw_steps.append((
        "read_file",
        "Read project facts, Makefile/CMakeLists, and existing peripheral configuration",
        ["Project layout and existing source code structure loaded"],
        ("Project root directory exists",),
    ))

    # 2. Knowledge or Skill query if needed
    if classification.modules:
        mod = classification.modules[0]
        cfg_tool = f"configure_{mod}"
        if cfg_tool in available_tools:
            raw_steps.append((
                cfg_tool,
                f"Generate standard {mod.upper()} hardware initialization code",
                [f"{mod.upper()} initialization source and header files created/patched"],
                ("Target peripheral parameters specified",),
            ))
        else:
            raw_steps.append((
                "apply_patch",
                f"Apply targeted diff for {mod.upper()} configuration",
                ["Patch applied without rejecting hunks"],
                ("Target source file exists",),
            ))
    elif wf.workflow == CoreWorkflow.FIX_COMPILE_ERROR.value:
        raw_steps.append((
            "apply_patch",
            "Apply minimal root-cause fix based on compiler error memory",
            ["Diff applied to resolve undefined symbol or configuration error"],
            ("Compiler error diagnostics available",),
        ))
    else:
        raw_steps.append((
            "apply_patch",
            "Apply code modifications meeting user requirement",
            ["Diff applied successfully"],
            ("Target source file exists",),
        ))

    # 3. Validation step
    if "validate_project" in available_tools:
        raw_steps.append((
            "validate_project",
            "Run static AST and peripheral rule validators",
            ["Peripheral initialization and clock enable checks passed"],
            ("Source code syntactically valid",),
        ))

    # 4. Compilation step
    raw_steps.append((
        "compile_project",
        "Build firmware using native cross-compiler toolchain",
        ["exit_code=0, non-empty firmware artifacts (ELF/HEX/BIN)"] if toolchain_ok else ["UNAVAILABLE locally unless cross-compiler toolchain is installed or running in CI/Docker"],
        ("Native cross-compiler toolchain available or running in CI runner",),
    ))

    # 5. Hardware steps if applicable
    if wf.hardware_intent:
        raw_steps.append((
            "flash_firmware",
            "Flash compiled ELF binary to target hardware via probe",
            ["Probe flash verification completed successfully"] if has_probe else ["UNAVAILABLE unless ST-Link or hardware probe detected"],
            ("Target hardware probe connected and detected",) if has_probe else ("ST-Link or hardware probe connected (currently missing)",),
        ))
        raw_steps.append((
            "serial_sample",
            "Capture UART stream to verify runtime markers and behavioral pass",
            [f"Serial marker (e.g. CEA:{target_platform.upper()}:PASS) observed"] if has_port else ["UNAVAILABLE unless serial COM port connected"],
            ("Serial COM port connected and enumerated",) if has_port else ("Serial COM port connected (currently missing)",),
        ))

    # Construct PlannedStep objects with policy metadata
    steps: list[PlannedStep] = []
    highest_risk = ToolRiskLevel.SAFE
    requires_approval = False

    for idx, (tool, reason, expected_ev, preconds) in enumerate(raw_steps, start=1):
        rule = ApprovalPolicyManager.get_rule(tool)
        spec = registry.get(tool) if tool in available_tools else None
        resume_pol = spec.resume_policy if spec else "replay"
        step_approval = rule.requires_approval or (spec.requires_approval if spec else False)

        if step_approval:
            requires_approval = True
        if rule.risk_level == ToolRiskLevel.DANGEROUS:
            highest_risk = ToolRiskLevel.DANGEROUS
        elif rule.risk_level == ToolRiskLevel.HARDWARE and highest_risk != ToolRiskLevel.DANGEROUS:
            highest_risk = ToolRiskLevel.HARDWARE
        elif rule.risk_level == ToolRiskLevel.WRITE and highest_risk == ToolRiskLevel.SAFE:
            highest_risk = ToolRiskLevel.WRITE

        steps.append(
            PlannedStep(
                id=f"step-{idx}",
                tool=tool,
                reason=reason,
                expected_evidence=expected_ev,
                preconditions=preconds,
                resume_policy=resume_pol,
                requires_approval=step_approval,
            )
        )

    return ActionPlan(
        goal=prompt.strip(),
        platform=target_platform,
        workflow=wf.workflow,
        steps=tuple(steps),
        risk=highest_risk.value,
        requires_approval=requires_approval,
    )
