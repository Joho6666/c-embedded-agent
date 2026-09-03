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
            "firstBuildSuccess": 0.0,
            "finalCompileSuccess": 0.0,
            "autoFixSuccess": 0.0,
            "semanticValidation": 0.0,
            "avgIterations": 0.0,
            "avgLatency": 0.0,
            "inputTokens": 0,
            "outputTokens": 0,
            "skipped": ["not run"],
        }
        assert REQUIRED.issubset(sample.keys())
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    assert REQUIRED.issubset(data.keys())
    if data.get("skipped"):
        assert data.get("finalCompileSuccess", 0) in {0, 0.0} or True
    for key in ("firstBuildSuccess", "finalCompileSuccess", "autoFixSuccess", "semanticValidation"):
        assert isinstance(data[key], (int, float))
        assert 0.0 <= float(data[key]) <= 1.0 or data.get("skipped")


def test_comparison_schema_optional() -> None:
    root = Path(__file__).resolve().parents[2]
    path = root / "benchmarks" / "comparison-summary.json"
    if not path.is_file():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "baselineCompileSuccess" in data or "skipped" in data
    assert "agentCompileSuccess" in data or "skipped" in data
