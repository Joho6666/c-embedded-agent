import json

import pytest

from app.agent.skill_router import SkillRouter
from app.skills.registry import DuplicateSkillError, SkillRegistry, default_skill_registry
from app.skills.schema import SkillValidationError


def test_split_catalog_is_valid_and_disabled_skill_does_not_auto_match() -> None:
    registry = default_skill_registry()
    assert len(registry.list()) == 11
    assert registry.get("freertos").enabled is False
    assert SkillRouter(registry).select("use FreeRTOS", platform="stm32f103").skills == ()


def test_composite_skill_wins_over_generic_skill() -> None:
    selected = SkillRouter().select("configure USART DMA reception", platform="stm32f103", context_level="PROJECT")
    assert [skill.id for skill in selected.skills] == ["usart-dma"]


def test_duplicate_ids_and_bad_status_are_rejected(tmp_path) -> None:
    folder = tmp_path / "stm32f103"
    folder.mkdir()
    base = {
        "id": "gpio", "name": "GPIO", "description": "x", "platforms": ["stm32f103"],
        "triggers": ["gpio"], "exclusions": [], "capabilities": [], "required_tools": [],
        "required_context": [], "validators": [], "golden_examples": [], "known_errors": [],
        "context_level": "FOCUSED", "enabled": True, "status": "ready",
    }
    (folder / "one.json").write_text(json.dumps(base), encoding="utf-8")
    (folder / "two.json").write_text(json.dumps(base), encoding="utf-8")
    with pytest.raises(DuplicateSkillError):
        SkillRegistry((tmp_path,))
    base["id"] = "bad"
    base["status"] = "invented"
    (folder / "two.json").write_text(json.dumps(base), encoding="utf-8")
    with pytest.raises(SkillValidationError):
        SkillRegistry((tmp_path,))
