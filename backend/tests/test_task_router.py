from app.agent.task_classifier import ContextLevel, TaskClassifier, TaskType
from app.agent.workflow_router import WorkflowRouter


def test_classifier_exposes_stable_contract() -> None:
    result = TaskClassifier().classify("修复 STM32F103 USART DMA 编译报错")
    assert result.task_type is TaskType.BUGFIX
    assert result.platform == "stm32f103"
    assert result.modules == ("usart", "dma")
    assert result.context_level is ContextLevel.PROJECT
    assert result.confidence > 0.5
    assert result.reasons


def test_architecture_and_release_use_deep_context() -> None:
    classifier = TaskClassifier()
    assert classifier.classify("重构 agent architecture").context_level is ContextLevel.DEEP
    assert classifier.classify("prepare release changelog").task_type is TaskType.RELEASE


def test_workflow_accumulates_multiple_peripheral_intents() -> None:
    decision = WorkflowRouter().route("新增 ADC DMA 采样并通过 USART 发送，同时输出 PWM")
    rendered = "\n".join(decision.steps)
    assert "ADC" in rendered
    assert "DMA" in rendered
    assert "USART" in rendered
    assert "PWM" in rendered


def test_hardware_workflow_is_the_only_one_with_device_group() -> None:
    normal = WorkflowRouter().route("实现 GPIO LED")
    hardware = WorkflowRouter().route("烧录固件并读取串口验证")
    assert "device" not in normal.allowed_tool_groups
    assert hardware.hardware_intent
    assert "device" in hardware.allowed_tool_groups
