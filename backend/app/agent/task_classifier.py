from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
import re


class TaskType(StrEnum):
    FEATURE = "feature"
    BUGFIX = "bugfix"
    PLATFORM = "platform"
    HARDWARE_DEBUG = "hardware_debug"
    ARCHITECTURE = "architecture"
    RELEASE = "release"


class ContextLevel(StrEnum):
    FOCUSED = "FOCUSED"
    PROJECT = "PROJECT"
    DEEP = "DEEP"


@dataclass(frozen=True)
class TaskClassification:
    task_type: TaskType
    platform: str | None
    modules: tuple[str, ...]
    context_level: ContextLevel
    confidence: float
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["task_type"] = self.task_type.value
        result["context_level"] = self.context_level.value
        result["modules"] = list(self.modules)
        result["reasons"] = list(self.reasons)
        return result


_MODULE_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("usart", ("usart", "uart", "serial", "串口")),
    ("adc", ("adc", "模数", "采样")),
    ("dma", ("dma",)),
    ("pwm", ("pwm", "servo", "舵机")),
    ("tim", ("tim", "timer", "定时器")),
    ("i2c", ("i2c", "eeprom")),
    ("spi", ("spi",)),
    ("exti", ("exti", "外部中断")),
    ("gpio", ("gpio", "led", "blink", "闪灯")),
)


def _has(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


class TaskClassifier:
    """Deterministic, explainable first-pass classifier.

    It deliberately exposes matching reasons rather than hidden chain-of-thought.
    Callers may replace it later with a model-backed classifier while preserving
    the return contract.
    """

    def classify(self, prompt: str, *, platform: str | None = None) -> TaskClassification:
        text = prompt.casefold()
        modules = tuple(name for name, words in _MODULE_PATTERNS if _has(text, words))
        reasons: list[str] = []

        detected_platform = platform
        if detected_platform is None:
            if _has(text, ("esp32-s3", "esp32s3", "esp-idf")):
                detected_platform = "esp32s3-idf"
            elif _has(text, ("stm32f103", "stm32f1", "blue pill", "蓝板")):
                detected_platform = "stm32f103"
        if detected_platform:
            reasons.append(f"platform:{detected_platform}")
        if modules:
            reasons.append("modules:" + ",".join(modules))

        if _has(text, ("release", "发布", "版本", "changelog")):
            task_type = TaskType.RELEASE
            level = ContextLevel.DEEP
            reasons.append("release intent")
        elif _has(text, ("架构", "architecture", "重构", "refactor", "迁移")):
            task_type = TaskType.ARCHITECTURE
            level = ContextLevel.DEEP
            reasons.append("architecture intent")
        elif _has(text, ("烧录", "flash", "真机", "硬件调试", "openocd", "串口验证")):
            task_type = TaskType.HARDWARE_DEBUG
            level = ContextLevel.PROJECT
            reasons.append("hardware intent")
        elif _has(text, ("新增平台", "支持平台", "new platform", "port to", "移植到")):
            task_type = TaskType.PLATFORM
            level = ContextLevel.DEEP
            reasons.append("platform implementation intent")
        elif _has(text, ("bug", "修复", "报错", "error", "失败", "fault", "崩溃")):
            task_type = TaskType.BUGFIX
            level = ContextLevel.PROJECT
            reasons.append("bugfix intent")
        else:
            task_type = TaskType.FEATURE
            level = ContextLevel.PROJECT if len(modules) > 1 or len(re.findall(r"\w+", text)) > 20 else ContextLevel.FOCUSED
            reasons.append("feature intent")

        confidence = min(0.98, 0.62 + 0.08 * bool(detected_platform) + 0.04 * min(len(modules), 4))
        return TaskClassification(task_type, detected_platform, modules, level, confidence, tuple(reasons))


def classify_task(prompt: str, *, platform: str | None = None) -> dict[str, object]:
    """Functional compatibility entry point for API and runtime integration."""

    return TaskClassifier().classify(prompt, platform=platform).to_dict()
