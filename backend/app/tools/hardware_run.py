from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from app.tools.compiler import CompileError, compile_project
from app.tools.error_memory import apply_known_fix, list_errors, mark_fix_result, record_from_output
from app.tools.flash import FlashError, detect_chip_id, flash_elf
from app.tools.debug_read import dump_fault
from app.tools.serialutil import connect as serial_connect
from app.tools.serialutil import disconnect as serial_disconnect
from app.tools.serialutil import status as serial_status
from app.tools.serialutil import wait_for as serial_wait_for
from app.tools.hw_session import load_session
from app.tools.validate import inspect_usart, validate_led_task
from app.validation import hardware_status, validate_project


def _get_git_sha(repo_root: Path) -> str:
    try:
        import subprocess

        proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True, text=True, timeout=5, check=False)
        return proc.stdout.strip() if proc.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def save_hardware_run_artifact(
    root: Path,
    run_id: str,
    *,
    platform_name: str = "STM32",
    mcu: str = "STM32F103C8T6",
    board: str = "Blue Pill",
    adapter: str = "stm32f103-hal",
    device: str | None = None,
    toolchain: str = "ARM_GCC",
    build_log: str = "",
    flash_log: str = "",
    serial_log: str = "",
    validation_data: dict[str, Any] | None = None,
) -> Path:
    from datetime import datetime, timezone
    import hashlib
    import json
    from app.config.settings import settings

    repo_root = getattr(settings, "repo_root", root)
    runs_dir = repo_root / "runs" / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)

    elf_path = root / "firmware.elf"
    elf_sha = ""
    if elf_path.is_file():
        try:
            elf_sha = hashlib.sha256(elf_path.read_bytes()).hexdigest()
        except OSError:
            elf_sha = ""

    metadata = {
        "runId": run_id,
        "platform": platform_name,
        "mcu": mcu,
        "board": board,
        "adapter": adapter,
        "firmwareArtifact": "firmware.elf" if elf_path.is_file() else None,
        "firmwareSha256": elf_sha or None,
        "toolchain": toolchain,
        "device": device,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gitSha": _get_git_sha(repo_root),
    }

    (runs_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    if build_log:
        (runs_dir / "build.log").write_text(build_log, encoding="utf-8")
    if flash_log:
        (runs_dir / "flash.log").write_text(flash_log, encoding="utf-8")
    if serial_log:
        (runs_dir / "serial.log").write_text(serial_log, encoding="utf-8")
    if validation_data:
        (runs_dir / "validation.json").write_text(json.dumps(validation_data, indent=2), encoding="utf-8")

    val_status = (validation_data or {}).get("status", "UNKNOWN")
    summary = {
        "runId": run_id,
        "platform": platform_name,
        "mcu": mcu,
        "status": val_status,
        "hasBuild": bool(build_log),
        "hasFlash": bool(flash_log),
        "hasSerial": bool(serial_log),
        "validated": bool(val_status in {"PASS", "VERIFIED_HARDWARE"}),
    }
    (runs_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return runs_dir


def _step(kind: str, title: str, status: str, detail: str = "", logs: str = "", reason: str = "") -> dict[str, Any]:
    return {
        "id": f"{kind}-{uuid.uuid4().hex[:6]}",
        "kind": kind,
        "title": title,
        "status": status,
        "detail": detail or None,
        "logs": logs or None,
        "reason": reason or None,
    }


def run_pipeline(
    root: Path,
    *,
    serial_device: str | None = None,
    baud: int = 115200,
    expect: str | None = None,
    task: str = "",
    max_hw_iterations: int = 3,
) -> dict[str, Any]:
    sess = load_session(root)
    serial_device = serial_device or sess.get("serialDevice")
    baud = int(baud or sess.get("baud") or 115200)
    last: dict[str, Any] | None = None
    for attempt in range(max(1, min(int(max_hw_iterations or 3), 3))):
        last = _run_pipeline_once(
            root,
            serial_device=serial_device,
            baud=baud,
            expect=expect,
            task=task,
            attempt=attempt + 1,
        )
        hw_run_id = last.get("runId")
        if hw_run_id:
            from app.agent.checkpoint import RunCheckpoint, save_run_checkpoint
            from app.config.settings import settings
            save_run_checkpoint(
                RunCheckpoint(
                    run_id=hw_run_id,
                    project_id=str(root.name),
                    prompt=task,
                    mode="hardware",
                    status="running" if attempt + 1 < 3 else "completed",
                    phase="hardware_loop",
                    hardware_attempt=attempt + 1,
                    last_errors=last.get("steps") or [],
                    serial_device=serial_device,
                    serial_baud=baud,
                    expect=expect,
                ),
                getattr(settings, "repo_root", root),
            )
        val = (last.get("validation") or {}).get("status")
        if val in {"PASS", "pass", "PARTIAL", "UNKNOWN", "UNAVAILABLE"}:
            last["hardwareIterations"] = attempt + 1
            return last
        if val in {"FAIL", "fail"} and attempt + 1 < 3:
            from app.tools.error_memory import apply_known_fix, match_known_errors

            blob = json_safe(last)
            for hit in match_known_errors(blob):
                if hit.get("mechanical"):
                    apply_known_fix(root, hit["id"])
            continue
        last["hardwareIterations"] = attempt + 1
        return last
    last = last or {"available": True, "steps": [], "validation": _unknown_val()}
    last["hardwareIterations"] = 3
    return last


def _run_pipeline_once(
    root: Path,
    *,
    serial_device: str | None = None,
    baud: int = 115200,
    expect: str | None = None,
    task: str = "",
    attempt: int = 1,
) -> dict[str, Any]:
    run_id = f"hw-{uuid.uuid4().hex[:8]}"
    steps: list[dict[str, Any]] = []

    try:
        build = compile_project(root)
    except CompileError as e:
        steps.append(_step("build", "Build", "failed", str(e), reason=str(e)))
        record_from_output(str(e), success=False)
        val = _unknown_val()
        save_hardware_run_artifact(root, run_id, build_log=str(e), validation_data=val)
        return {"available": True, "runId": run_id, "steps": steps, "validation": val}

    mem = build.get("memory") or {}
    flash_kb = mem.get("text") or mem.get("flash") or 0
    ram_kb = mem.get("data") or mem.get("ram") or 0
    ok = bool(build.get("success"))
    logs = str(build.get("combined") or "")[-4000:]
    steps.append(
        _step(
            "build",
            "Build",
            "success" if ok else "failed",
            f"firmware.elf  Flash {flash_kb}  RAM {ram_kb}" if ok else (build.get("error") or "compile failed"),
            logs,
        )
    )
    record_from_output(logs, success=ok)
    if not ok:
        val = _unknown_val()
        save_hardware_run_artifact(root, run_id, build_log=logs, validation_data=val)
        return {"available": True, "runId": run_id, "steps": steps, "validation": val}

    chip = detect_chip_id()
    if not chip.get("available"):
        steps.append(_step("detect", "ST-Link", "unavailable", "openocd / ST-Link 不可用", reason="Backend capability unavailable"))
        steps.append(_step("flash", "Flash", "unavailable", reason="Backend capability unavailable"))
        steps.append(_step("reset", "Reset", "unavailable", reason="skipped"))
        steps.append(_step("serial", "Serial", "unavailable", reason="skipped"))
        steps.append(_step("validate", "Validation", "unavailable", reason="no hardware evidence"))
        val = _unknown_val()
        save_hardware_run_artifact(root, run_id, build_log=logs, validation_data=val)
        return {"available": True, "runId": run_id, "steps": steps, "validation": val}

    family = chip.get("family") or "unknown"
    steps.append(_step("detect", "ST-Link", "success" if family == "STM32F1" else "failed", f"{family} detected", str(chip.get("output") or "")[-1500:]))

    flash_output = ""
    try:
        flashed = flash_elf(root)
        f_ok = bool(flashed.get("success"))
        flash_output = str(flashed.get("output") or "")
        steps.append(_step("flash", "Flash", "success" if f_ok else "failed", "Verified" if f_ok else "flash failed", flash_output[-2000:]))
        if f_ok:
            steps.append(_step("reset", "Reset", "success", "verify reset exit"))
        else:
            steps.append(_step("reset", "Reset", "failed", "flash did not reset"))
            steps.append(_step("serial", "Serial", "unavailable", reason="flash failed"))
            steps.append(_step("validate", "Validation", "unavailable", reason="flash failed"))
            val = _unknown_val()
            save_hardware_run_artifact(root, run_id, build_log=logs, flash_log=flash_output, validation_data=val)
            return {"available": True, "runId": run_id, "steps": steps, "validation": val}
    except FlashError as e:
        steps.append(_step("flash", "Flash", "failed", str(e), reason=str(e)))
        steps.append(_step("reset", "Reset", "unavailable", reason=str(e)))
        steps.append(_step("serial", "Serial", "unavailable", reason=str(e)))
        steps.append(_step("validate", "Validation", "unavailable", reason=str(e)))
        val = _unknown_val()
        save_hardware_run_artifact(root, run_id, build_log=logs, flash_log=str(e), validation_data=val)
        return {"available": True, "runId": run_id, "steps": steps, "validation": val}

    serial_lines: list[str] = []
    if serial_device:
        try:
            serial_connect(serial_device, baud)
            serial_lines = serial_wait_for(expect=expect, max_s=8.0, quiet=0.3)
            st = serial_status()
            steps.append(
                _step(
                    "serial",
                    "Serial",
                    "success" if serial_lines else "failed",
                    f"{st.get('device') or serial_device} {baud}",
                    "\n".join(serial_lines[-40:]),
                    reason="" if serial_lines else "no serial output",
                )
            )
        except (ValueError, RuntimeError, OSError) as e:
            steps.append(_step("serial", "Serial", "failed", str(e), reason=str(e)))
        finally:
            try:
                serial_disconnect()
            except Exception:
                pass
    else:
        steps.append(_step("serial", "Serial", "unavailable", "未指定串口", reason="no serial device"))

    if serial_device and not serial_lines:
        fault = dump_fault()
        steps.append(
            _step(
                "fault",
                "Fault dump",
                "unavailable" if not fault.get("available") else "failed",
                json_safe(fault.get("regs") or fault.get("reason")),
                json_safe(fault),
                reason=str(fault.get("reason") or "no serial; halt dump"),
            )
        )

    static = validate_led_task(root)
    semantic = validate_project(root, task)
    hw = hardware_status(
        serial_lines=serial_lines if serial_device else None,
        expect=expect,
        task=task or "led",
        has_probe=bool(serial_device),
    )
    status = hw.get("status") or "UNKNOWN"
    expected = expect or hw.get("reason") or ""
    actual = hw.get("observed") or hw.get("reason") or ""
    conf = 0.9 if status in {"PASS", "VERIFIED_HARDWARE"} else None
    step_status = {
        "PASS": "success",
        "VERIFIED_HARDWARE": "success",
        "FAIL": "failed",
        "PARTIAL": "failed",
        "UNKNOWN": "unavailable",
        "UNAVAILABLE": "unavailable",
        "MANUAL_STEP_REQUIRED": "waiting_manual",
    }.get(status, "unavailable")
    steps.append(
        _step(
            "validate",
            "Validation",
            step_status,
            f"{status} static={static.get('score')} semantic={semantic.get('score')}",
            json_safe({"static": static, "semantic": semantic, "hardware": hw}),
            reason="" if status in {"PASS", "VERIFIED_HARDWARE"} else str(hw.get("reason") or status),
        )
    )
    val_data = {
        "expected": expected,
        "actual": actual,
        "status": status,
        "confidence": conf,
        "semantic": semantic,
    }
    art_dir = save_hardware_run_artifact(
        root,
        run_id,
        device=serial_device,
        build_log=logs,
        flash_log=flash_output,
        serial_log="\n".join(serial_lines),
        validation_data=val_data,
    )
    return {
        "available": True,
        "runId": run_id,
        "artifactPath": str(art_dir),
        "attempt": attempt,
        "steps": steps,
        "validation": val_data,
    }



def json_safe(obj: Any) -> str:
    try:
        import json

        return json.dumps(obj, ensure_ascii=False)[:2000]
    except Exception:
        return str(obj)[:2000]


def _unknown_val() -> dict[str, Any]:
    return {"expected": "", "actual": "", "status": "UNAVAILABLE", "confidence": None, "reason": "Hardware Not Tested"}


def sample_serial(device: str, baud: int = 115200, seconds: float = 8.0, expect: str | None = None) -> dict[str, Any]:
    serial_connect(device, baud)
    try:
        lines = serial_wait_for(expect=expect, max_s=seconds, quiet=0.3)
        st = serial_status()
        return {"device": st.get("device") or device, "baud": baud, "lines": lines}
    finally:
        try:
            serial_disconnect()
        except Exception:
            pass


def auto_debug(
    root: Path,
    *,
    serial_device: str | None = None,
    baud: int = 115200,
    expect: str | None = None,
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    usart = inspect_usart(root)
    steps.append(
        _step(
            "autodebug",
            "Inspect USART / Clock / Pin",
            "success" if usart.get("passed") else "failed",
            f"score={usart.get('score')} missing={usart.get('missing')}",
            json_safe(usart),
        )
    )
    applied: list[str] = []
    for mid in usart.get("missing") or []:
        eid = None
        if mid in {"uart_source", "uart_module", "hal_uart_init"}:
            eid = "hal-uart-init-undef"
        if not eid:
            continue
        hits = list_errors(eid.replace("-", " "))
        steps.append(
            _step(
                "memory_match",
                "Error Memory",
                "success" if hits else "unavailable",
                hits[0]["pattern"] if hits else "no memory hit",
                json_safe(hits[:3]),
            )
        )
        fix = apply_known_fix(root, eid)
        if fix.get("applied"):
            applied.append(eid)
            steps.append(_step("autodebug", f"Apply {eid}", "success", ",".join(fix.get("files") or []), json_safe(fix)))
        else:
            steps.append(_step("autodebug", f"Apply {eid}", "unavailable", fix.get("reason") or "not applied", json_safe(fix)))

    pipeline = run_pipeline(root, serial_device=serial_device, baud=baud, expect=expect)
    for eid in applied:
        ok = bool(pipeline.get("steps") and pipeline["steps"][0].get("status") == "success")
        mark_fix_result(eid, success=ok)

    serial_fail = any(s.get("kind") == "serial" and s.get("status") in {"failed", "unavailable"} for s in pipeline.get("steps") or [])
    flash_ok = any(s.get("kind") == "flash" and s.get("status") == "success" for s in pipeline.get("steps") or [])
    extra = list(steps) + list(pipeline.get("steps") or [])
    val = pipeline.get("validation") or _unknown_val()
    if flash_ok and serial_fail:
        fault = dump_fault()
        extra.append(
            _step(
                "fault",
                "Fault dump",
                "unavailable" if not fault.get("available") else "failed",
                json_safe(fault.get("regs") or fault.get("reason")),
                json_safe(fault),
                reason=str(fault.get("reason") or "no serial after auto-debug"),
            )
        )
        val = {
            "expected": expect or "USART output",
            "actual": "no serial output after auto-debug",
            "status": "fail",
            "confidence": None,
            "fault": fault,
        }
        extra.append(
            _step(
                "validate",
                "Hardware Validation Failed",
                "failed",
                "Possible Causes: USART 未初始化 / GPIO AF / Baud / Clock / HardFault",
                reason="still no serial evidence",
            )
        )
    return {
        "available": True,
        "runId": pipeline.get("runId") or f"ad-{uuid.uuid4().hex[:8]}",
        "steps": extra,
        "validation": val,
    }
