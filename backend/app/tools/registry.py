from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
import inspect
from typing import Any, Callable, Iterable, Mapping


class ToolEffect(StrEnum):
    READ = "read"
    WORKSPACE_WRITE = "workspace_write"
    BUILD = "build"
    DEVICE = "device"


class ApprovalPolicy(StrEnum):
    NEVER = "never"
    MODE_DEPENDENT = "mode_dependent"
    ALWAYS = "always"


class ToolRegistryError(ValueError):
    pass


class ToolArgumentsError(ToolRegistryError):
    pass


class ToolUnavailableError(ToolRegistryError):
    pass


@dataclass(frozen=True)
class ToolAuthorization:
    allowed: bool
    requires_approval: bool = False
    reason: str | None = None


Availability = bool | Callable[[], bool | tuple[bool, str | None]]
Handler = Callable[..., Any]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    schema: Mapping[str, Any]
    handler: Handler | None = None
    effect: ToolEffect = ToolEffect.READ
    approval: ApprovalPolicy = ApprovalPolicy.NEVER
    availability: Availability = True
    group: str | None = None
    platforms: tuple[str, ...] = ("all",)
    risk: str = "safe"
    requires_approval: bool = False
    writes_files: bool = False
    uses_hardware: bool = False
    timeout: int = 30
    idempotent: bool = True
    resume_policy: str = "replay"  # replay, verify_before_retry, never_replay, skip
    replay_safe: bool = True
    irreversible: bool = False

    def openai_schema(self) -> dict[str, Any]:
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": dict(self.schema)}}

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "effect": self.effect.value,
            "group": self.group,
            "platforms": list(self.platforms),
            "risk": self.risk,
            "requiresApproval": self.requires_approval,
            "writesFiles": self.writes_files,
            "usesHardware": self.uses_hardware,
            "timeout": self.timeout,
            "idempotent": self.idempotent,
            "resumePolicy": self.resume_policy,
            "replaySafe": self.replay_safe,
            "irreversible": self.irreversible,
        }

    def available(self) -> tuple[bool, str | None]:
        value = self.availability() if callable(self.availability) else self.availability
        if isinstance(value, tuple):
            return bool(value[0]), value[1]
        return bool(value), None if value else "tool unavailable"

    def validate(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(arguments, Mapping):
            raise ToolArgumentsError(f"{self.name}: arguments must be an object")
        properties = self.schema.get("properties", {})
        required = self.schema.get("required", [])
        unknown = set(arguments) - set(properties)
        if unknown and self.schema.get("additionalProperties", False) is False:
            raise ToolArgumentsError(f"{self.name}: unknown arguments: {', '.join(sorted(unknown))}")
        missing = [key for key in required if key not in arguments]
        if missing:
            raise ToolArgumentsError(f"{self.name}: missing required arguments: {', '.join(missing)}")
        checked = dict(arguments)
        for key, value in checked.items():
            expected = properties.get(key, {}).get("type")
            valid = {
                "string": isinstance(value, str),
                "integer": isinstance(value, int) and not isinstance(value, bool),
                "number": isinstance(value, (int, float)) and not isinstance(value, bool),
                "boolean": isinstance(value, bool),
                "object": isinstance(value, Mapping),
                "array": isinstance(value, list),
            }.get(expected, True)
            if not valid:
                raise ToolArgumentsError(f"{self.name}: {key} must be {expected}")
            enum = properties.get(key, {}).get("enum")
            if enum is not None and value not in enum:
                raise ToolArgumentsError(f"{self.name}: {key} must be one of {enum}")
        return checked


class ToolRegistry:
    def __init__(self, specs: Iterable[ToolSpec] = ()) -> None:
        self._specs: dict[str, ToolSpec] = {}
        for spec in specs:
            self.register(spec)

    def register(self, spec: ToolSpec, *, replace_existing: bool = False) -> None:
        if spec.name in self._specs and not replace_existing:
            raise ToolRegistryError(f"duplicate tool {spec.name!r}")
        self._specs[spec.name] = spec

    def bind(self, name: str, handler: Handler, *, availability: Availability | None = None) -> None:
        spec = self.get(name)
        self._specs[name] = replace(spec, handler=handler, availability=spec.availability if availability is None else availability)

    def get(self, name: str) -> ToolSpec:
        try:
            return self._specs[name]
        except KeyError as exc:
            raise ToolRegistryError(f"unknown tool {name!r}") from exc

    def list(self, *, effects: set[ToolEffect] | None = None, groups: set[str] | None = None, available_only: bool = False) -> list[ToolSpec]:
        specs = self._specs.values()
        if effects is not None:
            specs = (spec for spec in specs if spec.effect in effects)
        if groups is not None:
            specs = (spec for spec in specs if (spec.group or spec.effect.value) in groups)
        if available_only:
            specs = (spec for spec in specs if spec.available()[0])
        return list(specs)

    def schemas(self, *, names: Iterable[str] | None = None, effects: set[ToolEffect] | None = None, groups: set[str] | None = None, available_only: bool = False) -> list[dict[str, Any]]:
        wanted = set(names) if names is not None else None
        return [spec.openai_schema() for spec in self.list(effects=effects, groups=groups, available_only=available_only) if wanted is None or spec.name in wanted]

    def authorize(
        self,
        name: str,
        mode: str,
        *,
        hardware_intent: bool = False,
        protected_path: bool = False,
        write_approved: bool = False,
        contained_path: bool = True,
        standard_write_path: bool = True,
    ) -> ToolAuthorization:
        spec = self.get(name)
        mode = mode.casefold()
        if mode not in {"plan", "code", "auto", "advanced"}:
            return ToolAuthorization(False, reason=f"unknown mode {mode!r}")
        if mode == "plan" and spec.effect is not ToolEffect.READ:
            return ToolAuthorization(False, reason="plan mode permits read-only tools")
        if spec.effect is ToolEffect.DEVICE:
            if not hardware_intent:
                return ToolAuthorization(False, reason="device tools require explicit hardware intent")
            return ToolAuthorization(True, True, "device tools always require separate approval")
        if spec.effect is ToolEffect.WORKSPACE_WRITE:
            if not contained_path:
                return ToolAuthorization(False, reason="workspace path containment failed")
            if mode == "code":
                return ToolAuthorization(True, True, "code mode requires approval for workspace writes")
            if mode == "auto" and not standard_write_path:
                return ToolAuthorization(False, reason="auto mode permits only standard writable paths")
            if protected_path:
                return ToolAuthorization(True, True, "protected paths always require approval")
            return ToolAuthorization(True, spec.approval is ApprovalPolicy.ALWAYS)
        if spec.effect is ToolEffect.BUILD and mode == "code" and not write_approved:
            return ToolAuthorization(False, reason="code mode build requires an approved modification")
        return ToolAuthorization(True, spec.approval is ApprovalPolicy.ALWAYS)

    def invoke(self, name: str, arguments: Mapping[str, Any]) -> Any:
        spec = self.get(name)
        available, reason = spec.available()
        if not available:
            raise ToolUnavailableError(f"{name}: {reason or 'unavailable'}")
        args = spec.validate(arguments)
        if spec.handler is None:
            raise ToolUnavailableError(f"{name}: no handler bound")
        result = spec.handler(**args)
        if inspect.isawaitable(result):
            raise ToolRegistryError(f"{name}: async handler requires invoke_async")
        return result

    async def invoke_async(self, name: str, arguments: Mapping[str, Any]) -> Any:
        spec = self.get(name)
        available, reason = spec.available()
        if not available:
            raise ToolUnavailableError(f"{name}: {reason or 'unavailable'}")
        args = spec.validate(arguments)
        if spec.handler is None:
            raise ToolUnavailableError(f"{name}: no handler bound")
        result = spec.handler(**args)
        return await result if inspect.isawaitable(result) else result


def _object(properties: dict[str, Any] | None = None, required: list[str] | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "object", "properties": properties or {}, "additionalProperties": False}
    if required:
        schema["required"] = required
    return schema


def _spec(
    name: str,
    description: str,
    effect: ToolEffect,
    properties: dict[str, Any] | None = None,
    required: list[str] | None = None,
    *,
    platforms: tuple[str, ...] = ("all",),
    risk: str | None = None,
    requires_approval: bool | None = None,
    writes_files: bool | None = None,
    uses_hardware: bool | None = None,
    timeout: int | None = None,
    idempotent: bool | None = None,
    resume_policy: str | None = None,
    replay_safe: bool | None = None,
    irreversible: bool = False,
) -> ToolSpec:
    approval = ApprovalPolicy.ALWAYS if effect is ToolEffect.DEVICE else ApprovalPolicy.MODE_DEPENDENT if effect is ToolEffect.WORKSPACE_WRITE else ApprovalPolicy.NEVER
    eff_risk = risk or ("hardware" if effect is ToolEffect.DEVICE else "write" if effect is ToolEffect.WORKSPACE_WRITE else "safe")
    eff_approval = requires_approval if requires_approval is not None else (effect in {ToolEffect.DEVICE, ToolEffect.WORKSPACE_WRITE})
    eff_writes = writes_files if writes_files is not None else (effect is ToolEffect.WORKSPACE_WRITE)
    eff_hw = uses_hardware if uses_hardware is not None else (effect is ToolEffect.DEVICE)
    eff_timeout = timeout if timeout is not None else (120 if effect is ToolEffect.BUILD else 30)

    # Derive idempotency & resume policy
    if idempotent is not None:
        eff_idempotent = idempotent
    elif effect in {ToolEffect.READ, ToolEffect.BUILD}:
        eff_idempotent = True
    elif name == "write_file":
        eff_idempotent = True
    elif name in {"serial_read", "read_register"}:
        eff_idempotent = True
    else:
        eff_idempotent = False

    if resume_policy is not None:
        eff_resume_policy = resume_policy
    elif irreversible:
        eff_resume_policy = "never_replay"
    elif effect in {ToolEffect.READ, ToolEffect.BUILD} or name in {"serial_read", "read_register"}:
        eff_resume_policy = "replay"
    else:
        eff_resume_policy = "verify_before_retry"

    if replay_safe is not None:
        eff_replay_safe = replay_safe
    else:
        eff_replay_safe = eff_idempotent and eff_resume_policy == "replay"

    # Derive platforms
    eff_platforms = platforms
    if any(k in name for k in ("hal_module", "usart", "adc", "pwm", "i2c", "spi", "exti", "register")):
        if "esp32" in name:
            eff_platforms = ("esp32s3-idf", "esp32")
        elif any(k in name for k in ("hal_module", "register", "pin_info", "mcu_info")):
            eff_platforms = ("stm32f103-hal", "stm32")

    return ToolSpec(
        name,
        description,
        _object(properties, required),
        effect=effect,
        approval=approval,
        group=effect.value,
        platforms=eff_platforms,
        risk=eff_risk,
        requires_approval=eff_approval,
        writes_files=eff_writes,
        uses_hardware=eff_hw,
        timeout=eff_timeout,
        idempotent=eff_idempotent,
        resume_policy=eff_resume_policy,
        replay_safe=eff_replay_safe,
        irreversible=irreversible,
    )


_S = {"type": "string"}
_I = {"type": "integer"}
DEFAULT_TOOL_SPECS = (
    _spec("list_files", "列出工程文件", ToolEffect.READ),
    _spec("read_file", "读取工程内文件", ToolEffect.READ, {"path": _S}, ["path"]),
    _spec("write_file", "写入工程内文件", ToolEffect.WORKSPACE_WRITE, {"path": _S, "content": _S}, ["path", "content"]),
    _spec("apply_patch", "应用 unified diff", ToolEffect.WORKSPACE_WRITE, {"path": _S, "patch": _S}, ["path", "patch"]),
    _spec("search_code", "在工程内搜索字符串", ToolEffect.READ, {"query": _S}, ["query"]),
    _spec("compile_project", "构建工程", ToolEffect.BUILD),
    _spec("retrieve_knowledge", "检索平台知识库", ToolEffect.READ, {"query": _S}, ["query"]),
    _spec("get_mcu_info", "读取 MCU 信息", ToolEffect.READ),
    _spec("get_pin_info", "查询引脚复用", ToolEffect.READ, {"pin": _S}, ["pin"]),
    _spec("flash_firmware", "烧录固件", ToolEffect.DEVICE),
    _spec("serial_read", "读取串口", ToolEffect.DEVICE, {"device": _S, "baud": _I, "expect": _S}, ["device"]),
    _spec("read_register", "读取调试寄存器", ToolEffect.DEVICE, {"name": _S}, ["name"]),
    _spec("read_symbol", "读取 ELF 符号", ToolEffect.READ, {"name": _S}, ["name"]),
    _spec("run_on_device", "构建、烧录并验证", ToolEffect.DEVICE, {"device": _S, "baud": _I, "expect": _S}),
    _spec("load_skill", "加载 Skill 摘要", ToolEffect.READ, {"id": _S}, ["id"]),
    _spec("search_error_memory", "搜索已知错误", ToolEffect.READ, {"query": _S, "tag": _S}, ["query"]),
    _spec("apply_error_memory_fix", "应用已知机械修复", ToolEffect.WORKSPACE_WRITE, {"id": _S}, ["id"]),
    _spec("register_hal_module", "登记 HAL 模块", ToolEffect.WORKSPACE_WRITE, {"module": _S}, ["module"]),
    _spec("configure_usart", "生成 USART 初始化", ToolEffect.WORKSPACE_WRITE, {"instance": _S, "baud": _I, "mode": _S}, ["instance"]),
    _spec("configure_adc", "生成 ADC 初始化", ToolEffect.WORKSPACE_WRITE, {"instance": _S, "channel": _I, "mode": _S}),
    _spec("configure_pwm", "生成 PWM 初始化", ToolEffect.WORKSPACE_WRITE, {"instance": _S, "channel": _I}),
    _spec("configure_i2c", "生成 I2C 初始化", ToolEffect.WORKSPACE_WRITE, {"instance": _S}),
    _spec("configure_spi", "生成 SPI 初始化", ToolEffect.WORKSPACE_WRITE, {"instance": _S}),
    _spec("configure_exti", "生成 EXTI 初始化", ToolEffect.WORKSPACE_WRITE, {"pin": _S, "edge": _S}),
)


def default_tool_registry() -> ToolRegistry:
    return ToolRegistry(DEFAULT_TOOL_SPECS)
