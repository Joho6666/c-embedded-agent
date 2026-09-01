from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from app.tools.ioc import parse_ioc
from app.workspace.manager import _ws_root, init_repo_safe
from app.workspace.paths import PathEscapeError, resolve_in_root


def scan_existing_project(src: Path) -> dict[str, Any]:
    root = Path(src)
    if not root.is_dir():
        return {"ok": False, "reason": f"not a directory: {src}", "warnings": ["path missing"]}
    files = [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()]
    iocs = [f for f in files if f.lower().endswith(".ioc")]
    startups = [f for f in files if Path(f).name.lower().startswith("startup") and f.lower().endswith((".s", ".S"))]
    lds = [f for f in files if f.lower().endswith(".ld")]
    core = [f for f in files if f.startswith("Core/")]
    drivers = [f for f in files if f.startswith("Drivers/")]
    middleware = [f for f in files if f.startswith("Middlewares/")]
    makefile = "Makefile" in files or "makefile" in files
    warnings: list[str] = []
    mcu = None
    cubemx = bool(iocs)
    ioc_name = iocs[0] if iocs else None
    if ioc_name:
        try:
            analysis = parse_ioc((root / ioc_name).read_text(encoding="utf-8", errors="replace"), ioc_name)
            mcu = analysis.get("mcu")
        except OSError as e:
            warnings.append(str(e))
            analysis = None
    else:
        analysis = None
    if not makefile:
        warnings.append("no Makefile")
    if not startups:
        warnings.append("no startup*.s")
    if not lds:
        warnings.append("no linker script")
    if not drivers:
        warnings.append("no Drivers/")
    framework = "HAL" if any("stm32f1xx_hal" in f.lower() for f in files) else "unknown"
    return {
        "ok": True,
        "mcu": mcu or "STM32F103C8T6",
        "framework": framework,
        "cubemx": cubemx,
        "ioc": ioc_name,
        "buildSystem": "make" if makefile else "unknown",
        "coreFiles": core[:80],
        "drivers": drivers[:40],
        "middlewares": middleware[:20],
        "startup": startups,
        "linker": lds,
        "warnings": warnings,
        "analysis": analysis,
    }


def import_existing_project(src: Path, name: str | None = None) -> dict[str, Any]:
    scan = scan_existing_project(src)
    if not scan.get("ok"):
        return scan
    import uuid

    pid = uuid.uuid4().hex[:12]
    dest = _ws_root() / pid
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("*.o", "*.elf", "*.hex", "*.bin", "*.map", ".git"))
    meta = {
        "id": pid,
        "name": name or Path(src).name,
        "platform": "STM32",
        "mcu": scan.get("mcu") or "STM32F103C8T6",
        "framework": scan.get("framework") or "HAL",
        "toolchain": "ARM_GCC",
        "board": "Blue Pill",
        "led": "PC13",
        "imported": True,
        "source": str(src),
        "ioc": scan.get("ioc"),
    }
    (dest / "project.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    if scan.get("analysis"):
        (dest / "ioc-analysis.json").write_text(json.dumps(scan["analysis"], indent=2), encoding="utf-8")
    init_repo_safe(dest)
    return {"ok": True, "projectId": pid, "scan": scan, "meta": meta}


def assert_import_path(rel: str) -> str:
    # Import copies a user-chosen directory; still reject obvious escapes in API wrappers.
    if ".." in Path(rel).parts:
        raise PathEscapeError(rel)
    return rel
