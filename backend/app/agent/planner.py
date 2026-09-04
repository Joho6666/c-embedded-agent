from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.agent.approvals import ApprovalPolicyManager, ToolRiskLevel
from app.agent.task_classifier import ContextLevel, TaskClassifier
from app.agent.workflow_router import CoreWorkflow, WorkflowRouter
from app.tools.registry import default_tool_registry


@dataclass(frozen=True)
class PlannedStep:
    tool: str
    reason: str
    expected_evidence: str

    def to_dict(self) -> dict[str, str]:
        return {
            "tool": self.tool,
            "reason": self.reason,
            "expected_evidence": self.expected_evidence,
        }


@dataclass(frozen=True)
class ActionPlan:
    goal: str
    platform: str
    steps: tuple[PlannedStep, ...]
    risk: str
    requires_approval: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "platform": self.platform,
            "steps": [s.to_dict() for s in self.steps],
            "risk": self.risk,
            "requires_approval": self.requires_approval,
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
    """Generate a rigorous, structured ActionPlan knowing platform, available tools, and risk."""
    classifier = TaskClassifier()
    classification = classifier.classify(prompt, platform=platform)
    target_platform = classification.platform or platform or "STM32"
    router = WorkflowRouter(classifier)
    wf = router.route(prompt, classification)

    registry = default_tool_registry()
    available_tools = {spec.name for spec in registry.list(available_only=False)}

    steps: list[PlannedStep] = []

    # 1. Understanding & Context step
    steps.append(
        PlannedStep(
            tool="read_file",
            reason="Read project facts, Makefile/CMakeLists, and existing peripheral configuration",
            expected_evidence="Project layout and existing source code structure loaded",
        )
    )

    # 2. Knowledge or Skill query if needed
    if classification.modules:
        mod = classification.modules[0]
        cfg_tool = f"configure_{mod}"
        if cfg_tool in available_tools:
            steps.append(
                PlannedStep(
                    tool=cfg_tool,
                    reason=f"Generate standard {mod.upper()} hardware initialization code",
                    expected_evidence=f"{mod.upper()} initialization source and header files created/patched",
                )
            )
        else:
            steps.append(
                PlannedStep(
                    tool="apply_patch",
                    reason=f"Apply targeted diff for {mod.upper()} configuration",
                    expected_evidence="Patch applied without rejecting hunks",
                )
            )
    elif wf.workflow == CoreWorkflow.FIX_COMPILE_ERROR.value:
        steps.append(
            PlannedStep(
                tool="apply_patch",
                reason="Apply minimal root-cause fix based on compiler error memory",
                expected_evidence="Diff applied to resolve undefined symbol or configuration error",
            )
        )
    else:
        steps.append(
            PlannedStep(
                tool="apply_patch",
                reason="Apply code modifications meeting user requirement",
                expected_evidence="Diff applied successfully",
            )
        )

    # 3. Validation step
    if "validate_project" in available_tools:
        steps.append(
            PlannedStep(
                tool="validate_project",
                reason="Run static AST and peripheral rule validators",
                expected_evidence="Peripheral initialization and clock enable checks passed",
            )
        )

    # 4. Compilation step
    steps.append(
        PlannedStep(
            tool="compile_project",
            reason="Build firmware using native cross-compiler toolchain",
            expected_evidence="exit_code=0, non-empty firmware artifacts (ELF/HEX/BIN)",
        )
    )

    # 5. Hardware steps if applicable
    if wf.hardware_intent:
        steps.append(
            PlannedStep(
                tool="flash_firmware",
                reason="Flash compiled ELF binary to target hardware via probe",
                expected_evidence="Probe flash verification completed successfully",
            )
        )
        steps.append(
            PlannedStep(
                tool="serial_sample",
                reason="Capture UART stream to verify runtime markers and behavioral pass",
                expected_evidence="Serial marker (e.g. CEA:STM32:PASS or CEA:ESP32:PASS) observed",
            )
        )

    # Determine overall risk and approval requirements
    highest_risk = ToolRiskLevel.SAFE
    requires_approval = False

    for s in steps:
        rule = ApprovalPolicyManager.get_rule(s.tool)
        if rule.requires_approval:
            requires_approval = True
        if rule.risk_level == ToolRiskLevel.DANGEROUS:
            highest_risk = ToolRiskLevel.DANGEROUS
        elif rule.risk_level == ToolRiskLevel.HARDWARE and highest_risk != ToolRiskLevel.DANGEROUS:
            highest_risk = ToolRiskLevel.HARDWARE
        elif rule.risk_level == ToolRiskLevel.WRITE and highest_risk == ToolRiskLevel.SAFE:
            highest_risk = ToolRiskLevel.WRITE

    return ActionPlan(
        goal=prompt.strip(),
        platform=target_platform,
        steps=tuple(steps),
        risk=highest_risk.value,
        requires_approval=requires_approval,
    )
