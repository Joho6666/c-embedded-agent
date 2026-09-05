from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def test_version_consistency() -> None:
    # 1. VERSION file
    version_file = ROOT / "VERSION"
    assert version_file.is_file()
    version = version_file.read_text(encoding="utf-8").strip()
    assert version == "0.9.1-beta"

    # 2. package.json
    pkg_file = ROOT / "package.json"
    assert pkg_file.is_file()
    pkg = json.loads(pkg_file.read_text(encoding="utf-8"))
    assert pkg.get("version") == version

    # 3. RELEASE_REPORT.md
    rel_file = ROOT / "RELEASE_REPORT.md"
    assert rel_file.is_file()
    rel_text = rel_file.read_text(encoding="utf-8")
    assert f"RELEASE_REPORT — C-Embedded Agent {version}" in rel_text
    assert f"App Version**: {version}" in rel_text

    # 4. PROJECT_STATE.md
    ps_file = ROOT / "PROJECT_STATE.md"
    assert ps_file.is_file()
    ps_text = ps_file.read_text(encoding="utf-8")
    assert f"Version target: **{version} — IN PROGRESS**" in ps_text

    # 5. README.md
    readme_file = ROOT / "README.md"
    assert readme_file.is_file()
    readme_text = readme_file.read_text(encoding="utf-8")
    assert f"Version: **{version}**" in readme_text

    # 6. backend release gates report
    from app.release.gates import evaluate_release_candidate
    report = evaluate_release_candidate(ROOT)
    assert report.version == version
    assert report.is_production_candidate is False
    assert "8051_golden" in report.gates
    assert report.gates["8051_golden"].passed is True
    assert report.gates["stm32_golden"].passed is True
    assert report.gates["esp32_smoke"].passed is True


def test_golden_counts_consistency() -> None:
    stm32_golden = [p for p in (ROOT / "examples" / "golden").iterdir() if p.is_dir() and p.name != "overlays" and (p / "Makefile").is_file()]
    esp32_golden = [p for p in (ROOT / "examples" / "golden_esp32").iterdir() if p.is_dir() and (p / "project.json").is_file()]
    mcu8051_golden = [p for p in (ROOT / "examples" / "golden_8051").iterdir() if p.is_dir() and (p / "Makefile").is_file()]

    assert len(stm32_golden) == 11
    assert len(esp32_golden) == 7
    assert len(mcu8051_golden) == 4

    # Check project_state.py consistency
    import scripts.project_state as ps
    state = ps.collect_state()
    assert state["version"] == "0.9.1-beta"
    assert state["stm32_golden_count"] == 11
    assert state["esp32_golden_count"] == 7
    assert state["mcu8051_golden_count"] == 4
    assert state["benchmark_task_count"] == 50
    assert "mcu8051-golden" in state["ci_jobs"]
    assert len(ps.check_documentation_drift(state)) == 0
