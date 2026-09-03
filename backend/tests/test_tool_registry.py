import pytest

from app.tools.registry import (
    DEFAULT_TOOL_SPECS,
    ToolArgumentsError,
    ToolEffect,
    ToolRegistry,
    ToolSpec,
    default_tool_registry,
)


def test_default_schema_and_registry_have_one_source_per_tool() -> None:
    registry = default_tool_registry()
    names = [spec.name for spec in DEFAULT_TOOL_SPECS]
    assert len(names) == len(set(names)) == 24
    assert [item["function"]["name"] for item in registry.schemas()] == names


def test_argument_validation_rejects_unknown_and_bad_types() -> None:
    spec = default_tool_registry().get("read_file")
    with pytest.raises(ToolArgumentsError):
        spec.validate({"path": "main.c", "surprise": True})
    with pytest.raises(ToolArgumentsError):
        spec.validate({"path": 1})


def test_permission_matrix() -> None:
    registry = default_tool_registry()
    assert registry.authorize("read_file", "plan").allowed
    assert not registry.authorize("apply_patch", "plan").allowed
    assert registry.authorize("apply_patch", "code").requires_approval
    assert not registry.authorize("compile_project", "code").allowed
    assert registry.authorize("compile_project", "code", write_approved=True).allowed
    assert not registry.authorize("flash_firmware", "advanced").allowed
    assert registry.authorize("flash_firmware", "advanced", hardware_intent=True).requires_approval
    assert registry.authorize("write_file", "auto", protected_path=True).requires_approval
    assert not registry.authorize("write_file", "advanced", contained_path=False).allowed
    assert not registry.authorize("write_file", "auto", standard_write_path=False).allowed


def test_bound_handler_is_validated_and_invoked() -> None:
    spec = ToolSpec(
        "echo", "echo", {"type": "object", "properties": {"value": {"type": "string"}}, "required": ["value"], "additionalProperties": False},
        effect=ToolEffect.READ,
    )
    registry = ToolRegistry((spec,))
    registry.bind("echo", lambda value: value.upper())
    assert registry.invoke("echo", {"value": "ok"}) == "OK"
