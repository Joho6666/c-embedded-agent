from __future__ import annotations

from app.agent.approvals import ApprovalPolicyManager, ToolRiskLevel
from app.agent.context_router import ContextRouter
from app.agent.planner import generate_action_plan, make_plan
from app.agent.workflow_router import CoreWorkflow, WorkflowRouter
from app.tools.registry import default_tool_registry


def test_structured_action_plan_output() -> None:
    plan = generate_action_plan("Configure USART1 to print telemetry", platform="STM32")
    assert plan.platform == "STM32"
    assert "USART" in plan.goal or "telemetry" in plan.goal
    assert len(plan.steps) >= 3

    # Steps must have tool, reason, expected_evidence
    tools = [s.tool for s in plan.steps]
    assert "read_file" in tools
    assert "compile_project" in tools

    plan_dict = plan.to_dict()
    assert plan_dict["workflow"]
    assert isinstance(plan_dict["steps"], list)

    for s_dict in plan_dict["steps"]:
        assert s_dict["id"].startswith("step-")
        assert s_dict["tool"]
        assert s_dict["reason"]
        assert isinstance(s_dict["expectedEvidence"], list)
        assert s_dict["resumePolicy"] in {"replay", "verify_before_retry", "never_replay", "skip"}
        assert isinstance(s_dict["requiresApproval"], bool)

    for step in plan.steps:
        assert step.tool
        assert step.reason
        assert step.expected_evidence

    # Step tools must exist in tool registry
    reg = default_tool_registry()
    for step in plan.steps:
        spec = reg.get(step.tool)
        assert spec is not None


def test_hardware_action_plan_requires_approval() -> None:
    plan = generate_action_plan("Flash firmware and verify serial output on hardware", platform="STM32")
    assert plan.risk in {"hardware", "dangerous"}
    assert plan.requires_approval is True
    tools = [s.tool for s in plan.steps]
    assert "flash_firmware" in tools
    assert "serial_sample" in tools

    # Verify no fake pass when probe is disconnected
    flash_step = next(s for s in plan.steps if s.tool == "flash_firmware")
    evidence_text = " ".join(flash_step.expected_evidence if isinstance(flash_step.expected_evidence, list) else [flash_step.expected_evidence])
    # When no physical probe is connected, expected evidence must state UNAVAILABLE
    assert "UNAVAILABLE" in evidence_text or "probe" in evidence_text.lower()



def test_approval_policy_manager_categories() -> None:
    safe_rule = ApprovalPolicyManager.get_rule("read_file")
    assert safe_rule.risk_level == ToolRiskLevel.SAFE
    assert safe_rule.requires_approval is False

    write_rule = ApprovalPolicyManager.get_rule("apply_patch")
    assert write_rule.risk_level == ToolRiskLevel.WRITE
    assert write_rule.writes_files is True

    hw_rule = ApprovalPolicyManager.get_rule("flash_firmware")
    assert hw_rule.risk_level == ToolRiskLevel.HARDWARE
    assert hw_rule.uses_hardware is True

    danger_rule = ApprovalPolicyManager.get_rule("erase_flash")
    assert danger_rule.risk_level == ToolRiskLevel.DANGEROUS
    assert danger_rule.requires_approval is True


def test_context_router_evidence_origins_traceability() -> None:
    router = ContextRouter()
    routed = router.route(
        context={"mcu": "STM32F103C8T6", "board": "Blue Pill", "adapterId": "stm32f103-hal"},
    )
    data = routed.to_dict()
    origins = data["_routing"]["evidenceOrigins"]
    assert origins.get("mcu") == "mcu_profile"
    assert origins.get("board") == "board_profile"
    assert origins.get("adapterId") == "platform_detection"


def test_core_workflows_identified() -> None:
    router = WorkflowRouter()
    assert router.route("新建工程并配置 LED").workflow in {CoreWorkflow.NEW_PROJECT.value, CoreWorkflow.ADD_PERIPHERAL.value}
    assert router.route("修复编译报错 undefined reference to HAL_UART_Init").workflow == CoreWorkflow.FIX_COMPILE_ERROR.value
    assert router.route("添加 ADC 采集通道").workflow == CoreWorkflow.ADD_PERIPHERAL.value
    assert router.route("硬件烧录并运行验证").workflow == CoreWorkflow.HARDWARE_VALIDATE.value
    assert router.route("串口失败排查 HardFault").workflow == CoreWorkflow.ANALYZE_SERIAL_FAILURE.value
