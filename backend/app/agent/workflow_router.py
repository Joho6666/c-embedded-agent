from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.agent.task_classifier import ContextLevel, TaskClassification, TaskClassifier, TaskType


class CoreWorkflow(StrEnum):
    NEW_PROJECT = "new_project"
    MODIFY_EXISTING_PROJECT = "modify_existing_project"
    FIX_COMPILE_ERROR = "fix_compile_error"
    ADD_PERIPHERAL = "add_peripheral"
    HARDWARE_VALIDATE = "hardware_validate"
    ANALYZE_SERIAL_FAILURE = "analyze_serial_failure"


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

    def identify_core_workflow(self, prompt: str, classification: TaskClassification) -> str:
        low = prompt.lower()
        if any(w in low for w in ("hardfault", "fault dump", "串口失败", "serial fail", "serial error", "无输出")):
            return CoreWorkflow.ANALYZE_SERIAL_FAILURE.value
        if classification.task_type is TaskType.HARDWARE_DEBUG or any(w in low for w in ("烧录", "flash", "hardware_validate", "真机验证")):
            return CoreWorkflow.HARDWARE_VALIDATE.value
        if classification.task_type is TaskType.BUGFIX or any(w in low for w in ("编译错误", "compile error", "build error", "报错", "undefined reference")):
            return CoreWorkflow.FIX_COMPILE_ERROR.value
        if any(w in low for w in ("新建工程", "创建工程", "new project", "template", "初始化工程")):
            return CoreWorkflow.NEW_PROJECT.value
        if classification.modules:
            return CoreWorkflow.ADD_PERIPHERAL.value
        return CoreWorkflow.MODIFY_EXISTING_PROJECT.value

    def route(self, prompt: str, classification: TaskClassification | None = None) -> WorkflowDecision:
        c = classification or self.classifier.classify(prompt)
        core_wf = self.identify_core_workflow(prompt, c)
        hardware = core_wf in {CoreWorkflow.HARDWARE_VALIDATE.value, CoreWorkflow.ANALYZE_SERIAL_FAILURE.value}

        groups = ["read"]
        if core_wf not in {TaskType.ARCHITECTURE.value, TaskType.RELEASE.value}:
            groups += ["workspace_write", "build"]
        if hardware:
            groups.append("device")

        # Specific workflows
        if core_wf == CoreWorkflow.ADD_PERIPHERAL.value:
            steps = ["读取工程与平台事实", "选择匹配的外设技能", "生成或增补外设补丁", "运行适用的静态验证", "编译并依据真实错误迭代", "验证最终产物非空"]
        elif core_wf == CoreWorkflow.FIX_COMPILE_ERROR.value:
            steps = ["复现问题并保存真实错误证据", "匹配 Error Memory 根因与已知修复", "应用最小化修复补丁", "执行编译回归验证"]
        elif core_wf == CoreWorkflow.HARDWARE_VALIDATE.value:
            steps = ["编译固件并验证 ELF/HEX/BIN 产物", "经单独审批后烧录至目标板卡", "复位并启动目标芯片", "采集串口或探针证据并验证期望标志"]
        elif core_wf == CoreWorkflow.ANALYZE_SERIAL_FAILURE.value:
            steps = ["采集串口输出与错误日志", "读取 CPU 寄存器与 HardFault 现场", "分析外设时钟、引脚或波特率配置", "给出诊断报告与修复方案"]
        elif core_wf == CoreWorkflow.NEW_PROJECT.value:
            steps = ["确认目标 MCU、开发板与框架", "从平台适配器克隆标准官方模板", "初始化工程配置文件与引脚定义", "验证首次模板编译通过"]
        else:
            steps = ["读取工程现状与依赖", "制定修改方案", "应用代码改动", "编译并依据真实错误迭代", "运行适用的静态验证"]

        # Ensure composite module steps if peripheral specific
        if core_wf == CoreWorkflow.ADD_PERIPHERAL.value:
            for m in c.modules:
                if m in _MODULE_STEPS and _MODULE_STEPS[m] not in steps:
                    steps.insert(3, _MODULE_STEPS[m])

        return WorkflowDecision(core_wf, c.context_level, tuple(dict.fromkeys(steps)), tuple(groups), hardware)


def route_workflow(prompt: str) -> dict[str, object]:
    return WorkflowRouter().route(prompt).to_dict()
