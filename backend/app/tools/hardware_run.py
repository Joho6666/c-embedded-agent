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
from app.tools.serialutil import timed_lines
from app.tools.serialutil import wait_for as serial_wait_for
from app.tools.hw_session import load_session
from app.tools.validate import inspect_usart, validate_led_task
from app.validation import hardware_status, validate_project
from app.hardware import session as hwrun


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


def _record_hardware_run(
    root: Path,
    run_rec: dict[str, Any],
    result: dict[str, Any],
    sess: dict[str, Any],
) -> dict[str, Any]:
    """Map pipeline steps onto the HardwareRun record and persist it.

    The PASS gate lives in hwrun.finalize_run: PASS requires flash success
    plus real hardware evidence — identical to the pipeline's own rules.
    """
    steps = result.get("steps") or []
    by_kind: dict[str, dict[str, Any]] = {}
    for s in steps:
        by_kind.setdefault(s.get("kind"), s)

    flash_step = by_kind.get("flash") or {}
    if flash_step.get("status") in {"success", "failed"}:  # only when actually attempted
        hwrun.set_flash_result(
            run_rec,
            "openocd -f interface/stlink.cfg -f target/stm32f1x.cfg -c program firmware.elf verify reset exit",
            {"success": flash_step.get("status") == "success", "exit_code": 0 if flash_step.get("status") == "success" else 1, "output": flash_step.get("logs") or flash_step.get("detail") or ""},
        )
    serial_step = by_kind.get("serial") or {}
    if serial_step:
        lines = [ln for ln in str(serial_step.get("logs") or "").splitlines() if ln]
        hwrun.set_serial_log(run_rec, lines)

    fault_step = by_kind.get("fault") or {}
    if fault_step:
        hwrun.add_evidence(
            run_rec,
            "DEBUGGER",
            {"claim": "fault register dump", "passed": False, "detail": fault_step.get("detail")},
        )

    val = result.get("validation") or {}
    raw_status = str(val.get("status") or "").upper()
    build_failed = (by_kind.get("build") or {}).get("status") == "failed"
    flash_failed = flash_step.get("status") == "failed"
    if raw_status in {"PASS", "FAIL", "PARTIAL", "UNKNOWN"}:
        status = raw_status
    elif flash_failed or build_failed:
        status = "FAIL"
    elif raw_status == "UNAVAILABLE":
        status = "UNAVAILABLE"
    else:
        status = "UNKNOWN"
    if status in {"PASS", "FAIL", "PARTIAL", "UNKNOWN"}:
        hwrun.add_evidence(
            run_rec,
            "HARDWARE",
            {
                "claim": f"hardware validation {status} (task={result.get('task') or 'led'})",
                "passed": status == "PASS",
                "detail": val,
            },
        )
    run_rec["task"] = result.get("task") or ""
    try:
        hwrun.finalize_run(run_rec, status)
    except hwrun.HardwareRunError:
        # PASS claimed without the required evidence — record honest PARTIAL
        status = "PARTIAL"
        hwrun.finalize_run(run_rec, status)
    result["runId"] = run_rec["runId"]
    hwrun.save_run(root, run_rec)

    # Outcome Memory: hardware runs feed the long-term record (real evidence only)
    try:
        from app.tools.outcome_memory import record_outcome

        record_outcome(
            run_id=run_rec["runId"],
            task_id=result.get("task") or None,
            task_type="hardware_run",
            domain=run_rec.get("board") or "hardware",
            agent="cea-hardware-pipeline",
            build_success=bool((run_rec.get("flashResult") or {}).get("success")) or build_succeeded(run_rec),
            simulation_success=False,
            hardware_success=status == "PASS",
            detail={"status": status, "steps": [s.get("kind") for s in result.get("steps") or []]},
        )
    except Exception:
        pass  # recording must never break the hardware pipeline
    return run_rec


def build_succeeded(run_rec: dict[str, Any]) -> bool:
    return bool(run_rec.get("firmwareHash") or run_rec.get("elfHash"))


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
    run_rec = hwrun.create_run(root, session=sess, platform="stm32")
    run_rec["task"] = task
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
        last["task"] = task
        val = (last.get("validation") or {}).get("status")
        if val in {"PASS", "pass", "PARTIAL", "UNKNOWN", "UNAVAILABLE"}:
            last["hardwareIterations"] = attempt + 1
            _record_hardware_run(root, run_rec, last, sess)
            return last
        if val in {"FAIL", "fail"} and attempt + 1 < 3:
            from app.tools.error_memory import apply_known_fix, match_known_errors

            blob = json_safe(last)
            for hit in match_known_errors(blob):
                if hit.get("mechanical"):
                    apply_known_fix(root, hit["id"])
            continue
        last["hardwareIterations"] = attempt + 1
        _record_hardware_run(root, run_rec, last, sess)
        return last
    last = last or {"available": True, "steps": [], "validation": _unknown_val()}
    last["hardwareIterations"] = 3
    _record_hardware_run(root, run_rec, last, sess)
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
    steps: list[dict[str, Any]] = []

    try:
        build = compile_project(root)
    except CompileError as e:
        steps.append(_step("build", "Build", "failed", str(e), reason=str(e)))
        record_from_output(str(e), success=False)
        return {"available": True, "runId": f"hw-{uuid.uuid4().hex[:8]}", "steps": steps}

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
        return {"available": True, "runId": f"hw-{uuid.uuid4().hex[:8]}", "steps": steps, "validation": _unknown_val()}

    chip = detect_chip_id()
    if not chip.get("available"):
        steps.append(_step("detect", "ST-Link", "unavailable", "openocd / ST-Link 不可用", reason="Backend capability unavailable"))
        steps.append(_step("flash", "Flash", "unavailable", reason="Backend capability unavailable"))
        steps.append(_step("reset", "Reset", "unavailable", reason="skipped"))
        steps.append(_step("serial", "Serial", "unavailable", reason="skipped"))
        steps.append(_step("validate", "Validation", "unavailable", reason="no hardware evidence"))
        return {"available": True, "runId": f"hw-{uuid.uuid4().hex[:8]}", "steps": steps, "validation": _unknown_val()}

    family = chip.get("family") or "unknown"
    steps.append(_step("detect", "ST-Link", "success" if family == "STM32F1" else "failed", f"{family} detected", str(chip.get("output") or "")[-1500:]))

    try:
        flashed = flash_elf(root)
        f_ok = bool(flashed.get("success"))
        steps.append(_step("flash", "Flash", "success" if f_ok else "failed", "Verified" if f_ok else "flash failed", str(flashed.get("output") or "")[-2000:]))
        if f_ok:
            steps.append(_step("reset", "Reset", "success", "verify reset exit"))
        else:
            steps.append(_step("reset", "Reset", "failed", "flash did not reset"))
            steps.append(_step("serial", "Serial", "unavailable", reason="flash failed"))
            steps.append(_step("validate", "Validation", "unavailable", reason="flash failed"))
            return {"available": True, "runId": f"hw-{uuid.uuid4().hex[:8]}", "steps": steps, "validation": _unknown_val()}
    except FlashError as e:
        steps.append(_step("flash", "Flash", "failed", str(e), reason=str(e)))
        steps.append(_step("reset", "Reset", "unavailable", reason=str(e)))
        steps.append(_step("serial", "Serial", "unavailable", reason=str(e)))
        steps.append(_step("validate", "Validation", "unavailable", reason=str(e)))
        return {"available": True, "runId": f"hw-{uuid.uuid4().hex[:8]}", "steps": steps, "validation": _unknown_val()}

    serial_lines: list[str] = []
    if serial_device:
        try:
            serial_connect(serial_device, baud)
            serial_lines = serial_wait_for(expect=expect, max_s=8.0, quiet=0.3)
            st = serial_status()
            timed = timed_lines()[-40:]
            serial_step = _step(
                "serial",
                "Serial",
                "success" if serial_lines else "failed",
                f"{st.get('device') or serial_device} {baud}",
                "\n".join(serial_lines[-40:]),
                reason="" if serial_lines else "no serial output",
            )
            serial_step["elapsed"] = [round(t, 3) for _, t in timed]
            steps.append(serial_step)
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
    conf = 0.9 if status == "PASS" else None
    step_status = {
        "PASS": "success",
        "FAIL": "failed",
        "PARTIAL": "failed",
        "UNKNOWN": "unavailable",
        "UNAVAILABLE": "unavailable",
    }.get(status, "unavailable")
    steps.append(
        _step(
            "validate",
            "Validation",
            step_status,
            f"{status} static={static.get('score')} semantic={semantic.get('score')}",
            json_safe({"static": static, "semantic": semantic, "hardware": hw}),
            reason="" if status == "PASS" else str(hw.get("reason") or status),
        )
    )
    return {
        "available": True,
        "runId": f"hw-{uuid.uuid4().hex[:8]}",
        "attempt": attempt,
        "steps": steps,
        "validation": {
            "expected": expected,
            "actual": actual,
            "status": status,
            "confidence": conf,
            "semantic": semantic,
        },
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
        timed = timed_lines()[-40:]
        return {
            "device": st.get("device") or device,
            "baud": baud,
            "lines": lines,
            "elapsed": [round(t, 3) for _, t in timed],
        }
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
    val_status = str((pipeline.get("validation") or {}).get("status") or "").upper()
    hw_pass = val_status == "PASS"
    build_ok = bool(pipeline.get("steps") and pipeline["steps"][0].get("status") == "success")
    for eid in applied:
        mark_fix_result(eid, success=build_ok, hardware_pass=hw_pass)

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
