from app.agent.context_router import CONTEXT_BUDGETS, ContextRouter, replace_current_context
from app.agent.task_classifier import ContextLevel


def test_context_budgets_and_priority_are_deterministic() -> None:
    source = {
        "mcu": "STM32F103C8T6",
        "errors": [{"message": "must remain"}],
        "relevant_files": ["x" * 4000 for _ in range(10)],
        "skills": [{"id": "gpio"}, {"id": "adc"}],
        "knowledge": ["k" * 4000],
        "project_tree": [f"Core/Src/f{i}.c" for i in range(1000)],
    }
    first = ContextRouter().route(source, level="FOCUSED")
    second = ContextRouter().route(source, level="FOCUSED")
    assert first == second
    assert first.budget == CONTEXT_BUDGETS[ContextLevel.FOCUSED] == 12_000
    assert first.used_chars <= first.budget
    assert first.context["platform_facts"]["mcu"] == "STM32F103C8T6"
    assert first.context["errors"][0]["message"] == "must remain"
    assert len(first.context["skills"]) <= 1


def test_context_levels_have_expected_budgets() -> None:
    router = ContextRouter()
    assert router.route(level="PROJECT").budget == 24_000
    assert router.route(level="DEEP").budget == 48_000


def test_current_context_is_replaced() -> None:
    messages = [{"role": "user", "content": "task"}]
    messages = replace_current_context(messages, "one")
    messages = replace_current_context(messages, "two")
    current = [m for m in messages if str(m.get("content", "")).startswith("[CURRENT_CONTEXT]")]
    assert len(current) == 1
    assert current[0]["content"].endswith("two")
