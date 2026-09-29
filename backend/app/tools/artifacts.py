"""Build artifact intelligence — sections, largest symbols, budgets, diffs.

Uses the real toolchain (arm-none-eabi-size -A, arm-none-eabi-nm --size-sort)
against the project's firmware.elf — no hand-parsing of ELF binaries.

Budget gates come from the project's `budgets` (project.json) when present,
otherwise from the MCU profile defaults (STM32F103C8T6: 64K flash / 20K RAM).
Over-budget is FAIL, within 90% is WARNING.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.tools.toolchain import prepend_toolchain_path

MCU_DEFAULTS = {"maxFlashBytes": 64 * 1024, "maxRamBytes": 20 * 1024}
SYMBOL_LIMIT = 12


def _find_tool(name: str) -> str | None:
    prepend_toolchain_path()
    return shutil.which(name)


def _sections(elf: Path) -> list[dict[str, Any]]:
    size = _find_tool("arm-none-eabi-size")
    if not size:
        return []
    try:
        r = subprocess.run(
            [size, "-A", str(elf)],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    out = []
    started = False
    for line in (r.stdout or "").splitlines():
        if line.strip().startswith("section"):
            started = True
            continue
        if not started or not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1].isdigit():
            name = parts[0]
            size_bytes = int(parts[1])
            if name in (".text", ".rodata", ".data", ".bss", ".isr_vector", ".ARM.attributes"):
                out.append({"name": name, "bytes": size_bytes})
    return out


def _largest_symbols(elf: Path) -> list[dict[str, Any]]:
    nm = _find_tool("arm-none-eabi-nm")
    if not nm:
        return []
    try:
        r = subprocess.run(
            [nm, "--size-sort", "--radix=d", str(elf)],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    out = []
    for line in (r.stdout or "").splitlines():
        parts = line.split()
        # nm --size-sort: <decimal-value> <type> <name>
        if len(parts) >= 3 and parts[0].isdigit():
            out.append({"name": parts[-1], "bytes": int(parts[0]), "type": parts[-2]})
    return sorted(out, key=lambda x: -x["bytes"])[:SYMBOL_LIMIT]


def _budgets(root: Path, sections: list[dict[str, Any]]) -> dict[str, Any]:
    budgets = {}
    pj = root / "project.json"
    if pj.is_file():
        try:
            budgets = (json.loads(pj.read_text(encoding="utf-8")) or {}).get("budgets") or {}
        except json.JSONDecodeError:
            budgets = {}
    max_flash = int(budgets.get("maxFlashBytes") or MCU_DEFAULTS["maxFlashBytes"])
    max_ram = int(budgets.get("maxRamBytes") or MCU_DEFAULTS["maxRamBytes"])
    by_name = {s["name"]: s["bytes"] for s in sections}
    flash_used = by_name.get(".text", 0) + by_name.get(".rodata", 0) + by_name.get(".data", 0)
    ram_used = by_name.get(".data", 0) + by_name.get(".bss", 0)

    def gate(used: int, limit: int) -> str:
        if used > limit:
            return "FAIL"
        if used >= 0.9 * limit:
            return "WARNING"
        return "OK"

    return {
        "flash": {"used": flash_used, "max": max_flash, "status": gate(flash_used, max_flash)},
        "ram": {"used": ram_used, "max": max_ram, "status": gate(ram_used, max_ram)},
    }


def analyze_artifacts(root: Path) -> dict[str, Any]:
    root = Path(root)
    elf = root / "firmware.elf"
    if not elf.is_file():
        return {
            "available": False,
            "status": "UNAVAILABLE",
            "reason": "firmware.elf missing — build first",
            "sections": [],
            "largestSymbols": [],
            "budgets": None,
        }
    sections = _sections(elf)
    if not sections:
        return {
            "available": False,
            "status": "UNAVAILABLE",
            "reason": "arm-none-eabi-size unavailable",
            "sections": [],
            "largestSymbols": [],
            "budgets": None,
        }
    budgets = _budgets(root, sections)
    overall = "FAIL" if "FAIL" in (budgets["flash"]["status"], budgets["ram"]["status"]) else (
        "WARNING" if "WARNING" in (budgets["flash"]["status"], budgets["ram"]["status"]) else "OK"
    )
    return {
        "available": True,
        "status": overall,
        "elf": str(elf),
        "elfSize": elf.stat().st_size,
        "sections": sections,
        "largestSymbols": _largest_symbols(elf),
        "budgets": budgets,
        "note": "budget gates are per-project; MCU defaults only when the project sets none",
    }


def firmware_change(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """FirmwareChangeReport: resource deltas + symbol movement between builds."""
    if not (before.get("available") and after.get("available")):
        return {
            "available": False,
            "status": "UNAVAILABLE",
            "reason": "both builds must have artifact analysis",
        }

    def by_name(sections: list[dict[str, Any]]) -> dict[str, int]:
        return {s["name"]: s["bytes"] for s in sections}

    b, a = by_name(before["sections"]), by_name(after["sections"])
    flash_delta = (
        (a.get(".text", 0) + a.get(".rodata", 0) + a.get(".data", 0))
        - (b.get(".text", 0) + b.get(".rodata", 0) + b.get(".data", 0))
    )
    ram_delta = (a.get(".data", 0) + a.get(".bss", 0)) - (b.get(".data", 0) + b.get(".bss", 0))

    bs = {s["name"]: s["bytes"] for s in before.get("largestSymbols") or []}
    asyms = {s["name"]: s["bytes"] for s in after.get("largestSymbols") or []}
    risk_notes = []
    if flash_delta > 0:
        risk_notes.append(f"flash +{flash_delta} bytes — verify flash budget on small MCUs")
    if ram_delta > 0:
        risk_notes.append(f"RAM +{ram_delta} bytes — watch stack margin")
    for name in asyms:
        if name in bs and asyms[name] - bs[name] > 64:
            risk_notes.append(f"symbol {name} grew by {asyms[name] - bs[name]} bytes")

    return {
        "available": True,
        "status": "SUCCESS",
        "flashDelta": flash_delta,
        "ramDelta": ram_delta,
        "sectionDeltas": {k: a.get(k, 0) - b.get(k, 0) for k in sorted(set(b) | set(a))},
        "newSymbols": sorted(set(asyms) - set(bs)),
        "removedSymbols": sorted(set(bs) - set(asyms)),
        "budgetStatusAfter": after.get("budgets"),
        "riskNotes": risk_notes,
    }
