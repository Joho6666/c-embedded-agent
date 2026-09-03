from __future__ import annotations

from dataclasses import dataclass

from app.agent.task_classifier import ContextLevel, TaskClassification, TaskClassifier, TaskType


@dataclass(frozen=True)
class WorkflowDecision:
    workflow: str
    context_level: ContextLevel
    steps: tuple[str, ...]
    allowed_tool_groups: tuple[str, ...]
    hardware_intent: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "workflow": self.workflow,
            "context_level": self.context_level.value,
            "steps": list(self.steps),
            "allowed_tool_groups": list(self.allowed_tool_groups),
            "hardware_intent": self.hardware_intent,
        }


_MODULE_STEPS = {
    "gpio": "配置 GPIO 与引脚占用",
    "exti": "配置 EXTI、NVIC 与中断处理",
    "usart": "配置 USART、GPIO 与 MSP",
    "dma": "配置 DMA 通道、中断与外设关联",
    "adc": "配置 ADC 通道与采样路径",
    "pwm": "配置定时器 PWM 通道并启动输出",
    "tim": "配置定时器时基与中断",
    "i2c": "配置 I2C 引脚、时钟与总线参数",
    "spi": "配置 SPI 引脚、时钟与传输参数",
}


class WorkflowRouter:
    def __init__(self, classifier: TaskClassifier | None = None) -> None:
        self.classifier = classifier or TaskClassifier()

    def route(self, prompt: str, classification: TaskClassification | None = None) -> WorkflowDecision:
        c = classification or self.classifier.classify(prompt)
        hardware = c.task_type is TaskType.HARDWARE_DEBUG
        groups = ["read"]
        if c.task_type not in {TaskType.ARCHITECTURE, TaskType.RELEASE}:
            groups += ["workspace_write", "build"]
        if hardware:
            groups.append("device")

        prefix = {
            TaskType.FEATURE: ("读取工程与平台事实", "确认需求与受影响模块"),
            TaskType.BUGFIX: ("复现问题并保存真实错误证据", "定位最小根因"),
            TaskType.PLATFORM: ("检查平台注册契约与工程特征", "实现平台能力闭环"),
            TaskType.HARDWARE_DEBUG: ("确认设备、端口与硬件意图", "构建固件并保留产物证据"),
            TaskType.ARCHITECTURE: ("绘制当前依赖与兼容边界", "设计并验证架构改动"),
            TaskType.RELEASE: ("运行完整发布门禁", "汇总版本、兼容性与证据"),
        }[c.task_type]
        steps = list(prefix)
        # Add every matched module in stable order; composite tasks must not lose intents.
        steps.extend(_MODULE_STEPS[module] for module in c.modules if module in _MODULE_STEPS)
        if c.task_type not in {TaskType.ARCHITECTURE, TaskType.RELEASE}:
            steps += ["编译并依据真实错误迭代", "运行适用的静态验证"]
        if hardware:
            steps += ["经单独审批后烧录", "采集串口或探针证据并验证"]
        return WorkflowDecision(c.task_type.value, c.context_level, tuple(dict.fromkeys(steps)), tuple(groups), hardware)


def route_workflow(prompt: str) -> dict[str, object]:
    return WorkflowRouter().route(prompt).to_dict()
