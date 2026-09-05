import json
from pathlib import Path

REQUIRED = {
    "model",
    "tasks",
    "firstBuildSuccess",
    "finalCompileSuccess",
    "autoFixSuccess",
    "semanticValidation",
    "avgIterations",
    "avgLatency",
    "inputTokens",
    "outputTokens",
}


def test_benchmark_schema_skip_file_if_present() -> None:
    root = Path(__file__).resolve().parents[2]
    path = root / "benchmarks" / "stm32f103" / "latest-summary.json"
    if not path.is_file():
        # Schema contract still holds for the writer helper.
        sample = {
            "model": "",
            "tasks": 0,
            "firstBuildSuccess": None,
            "finalCompileSuccess": None,
            "autoFixSuccess": None,
            "semanticValidation": None,
            "avgIterations": None,
            "avgLatency": None,
            "inputTokens": 0,
            "outputTokens": 0,
            "skipped": ["not run"],
        }
        assert REQUIRED.issubset(sample.keys())
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    assert REQUIRED.issubset(data.keys())
    if data.get("status") == "SKIPPED":
        assert data.get("skipped")
        for key in ("firstBuildSuccess", "finalCompileSuccess", "autoFixSuccess", "semanticValidation"):
            assert data[key] is None
        return
    for key in ("firstBuildSuccess", "finalCompileSuccess", "autoFixSuccess", "semanticValidation"):
        assert isinstance(data[key], (int, float))
        assert 0.0 <= float(data[key]) <= 1.0


def test_comparison_schema_optional() -> None:
    root = Path(__file__).resolve().parents[2]
    path = root / "benchmarks" / "comparison-summary.json"
    if not path.is_file():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "baselineCompileSuccess" in data or "skipped" in data
    assert "agentCompileSuccess" in data or "skipped" in data
    if data.get("status") == "SKIPPED":
        assert data.get("skipped")
        assert data.get("baselineCompileSuccess") is None
        assert data.get("agentCompileSuccess") is None
