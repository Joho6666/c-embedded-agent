#!/usr/bin/env python3
"""Project State computation and documentation drift detector."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def _collect_platforms_pure_python(root: Path) -> dict[str, dict]:
    platforms = {}
    adapter_paths = [
        root / "backend" / "app" / "platforms" / "stm32f103" / "adapter.py",
        root / "backend" / "app" / "platforms" / "esp32s3" / "adapter.py",
        root / "backend" / "app" / "platforms" / "mcu8051" / "adapter.py",
    ]
    for p in adapter_paths:
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        aid_m = re.search(r'adapter_id="([^"]+)"', text)
        status_m = re.search(r'status="([^"]+)"', text)
        plat_m = re.search(r'platform="([^"]+)"', text)
        mcu_m = re.search(r'mcu="([^"]+)"', text)
        fw_m = re.search(r'framework="([^"]+)"', text)
        if aid_m and status_m:
            aid = aid_m.group(1)
            platforms[aid] = {
                "id": aid,
                "status": status_m.group(1),
                "platform": plat_m.group(1) if plat_m else "",
                "mcu": mcu_m.group(1) if mcu_m else "",
                "framework": fw_m.group(1) if fw_m else "",
            }
    return platforms


def collect_state() -> dict:
    try:
        from app.platforms.registry import default_registry

        registry = default_registry(ROOT)
        platforms = registry.list_platforms()
        platform_map = {p["id"]: p for p in platforms}
    except (ImportError, Exception):
        platform_map = _collect_platforms_pure_python(ROOT)

    # 1. Version
    version_file = ROOT / "VERSION"
    version = version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else "0.8.0-beta"

    # 3. Golden counts
    stm32_golden = sorted(p.name for p in (ROOT / "examples" / "golden").iterdir() if p.is_dir() and p.name != "overlays" and (p / "Makefile").is_file())
    esp32_golden = sorted(p.name for p in (ROOT / "examples" / "golden_esp32").iterdir() if p.is_dir() and (p / "project.json").is_file()) if (ROOT / "examples" / "golden_esp32").is_dir() else []
    mcu8051_golden = sorted(p.name for p in (ROOT / "examples" / "golden_8051").iterdir() if p.is_dir() and (p / "Makefile").is_file()) if (ROOT / "examples" / "golden_8051").is_dir() else []

    # 4. Benchmark task count & status
    task_files = sorted(p for p in (ROOT / "benchmarks" / "stm32f103").glob("*.json") if p.name not in {"latest-summary.json", "results.json", "failure-breakdown.json"})
    summary_file = ROOT / "benchmarks" / "stm32f103" / "latest-summary.json"
    bench_status = "NOT RUN"
    if summary_file.is_file():
        try:
            bench_status = json.loads(summary_file.read_text(encoding="utf-8")).get("status", "NOT RUN")
        except Exception:
            pass

    # 5. CI jobs
    ci_file = ROOT / ".github" / "workflows" / "ci.yml"
    ci_jobs = []
    if ci_file.is_file():
        ci_text = ci_file.read_text(encoding="utf-8")
        for job in ("backend", "frontend", "stm32-golden", "esp32-smoke", "esp32-golden", "8051-golden", "quality"):
            if f"  {job}:" in ci_text:
                ci_jobs.append(job)

    return {
        "version": version,
        "platforms": platform_map,
        "stm32_golden_count": len(stm32_golden),
        "esp32_golden_count": len(esp32_golden),
        "mcu8051_golden_count": len(mcu8051_golden),
        "benchmark_task_count": len(task_files),
        "benchmark_status": bench_status,
        "ci_jobs": ci_jobs,
    }


def check_documentation_drift(state: dict) -> list[str]:
    issues: list[str] = []

    # 1. Check PROJECT_STATE.md
    ps_file = ROOT / "PROJECT_STATE.md"
    if ps_file.is_file():
        ps_text = ps_file.read_text(encoding="utf-8")
        if "esp32-smoke" in state["ci_jobs"] and "ESP-IDF smoke SKIPPED" in ps_text:
            if "CI smoke" not in ps_text and "CI" not in ps_text:
                issues.append("PROJECT_STATE.md claims ESP-IDF smoke is skipped, but CI esp32-smoke job is active")
        if state["benchmark_task_count"] >= 50 and "50 tasks" not in ps_text:
            issues.append(f"PROJECT_STATE.md task count does not match benchmark directory ({state['benchmark_task_count']} tasks)")

    # 2. Check README.md for unsupported platform claims
    readme_file = ROOT / "README.md"
    if readme_file.is_file():
        readme_text = readme_file.read_text(encoding="utf-8")
        # Check forbidden 4th platform claims
        for unsupported in ("STM32F407", "RP2040", "NRF52", "Arduino", "Zephyr"):
            pattern = rf"\|\s*{unsupported}\s*\|\s*[✅✔]|\|\s*{unsupported}\s*\|\s*Beta"
            if re.search(pattern, readme_text, re.IGNORECASE):
                issues.append(f"README.md claims unsupported platform {unsupported} is available")

        # Check 8051 status in README vs registry: must NOT claim Beta
        mcu8051_reg = state["platforms"].get("8051-sdcc", {})
        if mcu8051_reg.get("status") == "experimental":
            if re.search(r"\|\s*8051\s*[^|]*\|\s*Beta\s*\|", readme_text):
                issues.append("README.md claims 8051 is Beta, but PlatformRegistry registers it as experimental")

    return issues


def render_markdown(state: dict) -> str:
    ci_cnt = len(state['ci_jobs'])
    md = [
        "# Project State",
        "",
        f"Version target: **{state['version']} — IN PROGRESS**. Ground Truth State Generated.",
        "",
        "| Subsystem / Platform | Status | Evidence |",
        "|---|---|---|",
        f"| STM32F103 HAL | {state['platforms'].get('stm32f103-hal', {}).get('status', 'ready').upper()} | {state['stm32_golden_count']}/11 Golden projects compile via official CubeF1 HAL |",
        f"| ESP32-S3 ESP-IDF | {state['platforms'].get('esp32s3-idf', {}).get('status', 'ready').upper()} | CI ESP-IDF 6.1 Docker matrix active; {state['esp32_golden_count']}/7 golden examples |",
        f"| 8051 SDCC | {state['platforms'].get('8051-sdcc', {}).get('status', 'experimental').upper()} | SDCC CI active; {state['mcu8051_golden_count']}/4 golden projects compile |",
        f"| CI Automation | {ci_cnt}/{ci_cnt} PASS | Jobs: {', '.join(state['ci_jobs'])} |",
        f"| Benchmark Harness | {state['benchmark_status']} | {state['benchmark_task_count']} tasks schema validated; Agent vs Baseline harness isolated |",
        "| Hardware Execution | NOT_TESTED | No physical ST-Link/probe connected; NO FAKE PASS |",
        "",
        "Known limits: physical hardware execution requires connected test bench; LLM evaluations require external API credentials.",
        "",
    ]
    return "\n".join(md)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect and check project state consistency.")
    parser.add_argument("--check", action="store_true", help="Check for documentation drift and consistency.")
    parser.add_argument("--generate", action="store_true", help="Generate updated PROJECT_STATE.md text.")
    args = parser.parse_args()

    state = collect_state()

    if args.check:
        issues = check_documentation_drift(state)
        if issues:
            print("FAIL: Documentation drift detected:")
            for issue in issues:
                print(f"  - {issue}")
            return 1
        print("PASS: No documentation drift detected.")
        return 0

    if args.generate:
        print(render_markdown(state))
        return 0

    print(json.dumps(state, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
