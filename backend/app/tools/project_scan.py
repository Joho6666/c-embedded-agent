from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from app.config.settings import settings
from app.platforms.registry import Resolution, default_registry
from app.tools.ioc import parse_ioc
from app.workspace.manager import _ws_root, init_repo_safe
from app.workspace.paths import PathEscapeError


def scan_existing_project(src: Path) -> dict[str, Any]:
    root = Path(src)
    if not root.is_dir():
        return {
            "ok": False,
            "status": "unsupported",
            "reason": f"not a directory: {src}",
            "warnings": ["path missing"],
            "evidence": [],
        }
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
    registry = default_registry(settings.repo_root)
    resolution = _normalized_resolution(registry.detect(root))
    evidence = [item.to_dict() for item in resolution.evidence]
    if resolution.status != "resolved" or resolution.adapter is None:
        return {
            "ok": False,
            "status": resolution.status,
            "reason": resolution.reason or "no registered platform matched the project",
            "adapterId": None,
            "mcu": mcu,
            "framework": "unknown",
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
            "evidence": evidence,
        }

    adapter = resolution.adapter
    descriptor = adapter.descriptor
    context = adapter.load_context(root)
    facts = dict(context.get("facts") or {})
    if adapter.adapter_id == "stm32f103-hal":
        if not makefile:
            warnings.append("no Makefile")
        if not startups:
            warnings.append("no startup*.s")
        if not lds:
            warnings.append("no linker script")
        if not drivers:
            warnings.append("no Drivers/")
    elif adapter.adapter_id == "esp32s3-idf":
        if "CMakeLists.txt" not in files:
            warnings.append("no CMakeLists.txt")
        if not any(f.startswith("main/") for f in files):
            warnings.append("no main component")

    build_system = "make" if makefile else "unknown"
    if adapter.adapter_id == "esp32s3-idf" and "CMakeLists.txt" in files:
        build_system = "esp-idf"
    return {
        "ok": True,
        "status": "resolved",
        "adapterId": adapter.adapter_id,
        "platform": descriptor.platform,
        "mcu": mcu or facts.get("mcu") or descriptor.mcu,
        "framework": facts.get("framework") or descriptor.framework,
        "board": facts.get("board"),
        "toolchain": facts.get("toolchain") or (descriptor.toolchains[0] if descriptor.toolchains else None),
        "capabilities": list(descriptor.capabilities),
        "cubemx": cubemx,
        "ioc": ioc_name,
        "buildSystem": build_system,
        "coreFiles": core[:80],
        "drivers": drivers[:40],
        "middlewares": middleware[:20],
        "startup": startups,
        "linker": lds,
        "warnings": warnings,
        "analysis": analysis,
        "evidence": evidence,
    }


def import_existing_project(src: Path, name: str | None = None) -> dict[str, Any]:
    scan = scan_existing_project(src)
    if not scan.get("ok"):
        return scan
    adapter_id = str(scan.get("adapterId") or "")
    adapter = default_registry(settings.repo_root).get(adapter_id)
    if adapter is None:
        return {
            "ok": False,
            "status": "unsupported",
            "reason": f"registered adapter is unavailable: {adapter_id}",
            "scan": scan,
        }
    import uuid

    pid = uuid.uuid4().hex[:12]
    dest = _ws_root() / pid
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("*.o", "*.elf", "*.hex", "*.bin", "*.map", ".git"))
    meta = {
        "id": pid,
        "name": name or Path(src).name,
        "platform": scan.get("platform") or adapter.descriptor.platform,
        "mcu": scan.get("mcu") or adapter.descriptor.mcu,
        "framework": scan.get("framework") or adapter.descriptor.framework,
        "toolchain": scan.get("toolchain"),
        "board": scan.get("board"),
        "adapterId": adapter.adapter_id,
        "capabilities": list(adapter.descriptor.capabilities),
        "imported": True,
        "source": str(src),
        "ioc": scan.get("ioc"),
    }
    (dest / "project.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    if scan.get("analysis"):
        (dest / "ioc-analysis.json").write_text(json.dumps(scan["analysis"], indent=2), encoding="utf-8")
    init_repo_safe(dest)
    return {"ok": True, "projectId": pid, "scan": scan, "meta": meta}


def _normalized_resolution(resolution: Resolution) -> Resolution:
    """Preserve conflicting cross-platform evidence as an explicit ambiguity.

    Individual adapters reject a match when another platform's signature is
    present. When two adapters both report positive reasons, that is still a
    conflict rather than an unknown project and must not be silently resolved.
    """
    if resolution.status != "unsupported":
        return resolution
    candidates = [item.adapter_id for item in resolution.evidence if item.reasons]
    if len(candidates) < 2:
        return resolution
    return Resolution(
        "ambiguous",
        reason="conflicting platform signatures: " + ", ".join(sorted(candidates)),
        evidence=resolution.evidence,
    )


def assert_import_path(rel: str) -> str:
    # Import copies a user-chosen directory; still reject obvious escapes in API wrappers.
    if ".." in Path(rel).parts:
        raise PathEscapeError(rel)
    return rel
