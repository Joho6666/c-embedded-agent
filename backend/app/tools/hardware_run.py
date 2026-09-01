from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from app.tools.compiler import CompileError, compile_project
from app.tools.error_memory import apply_known_fix, list_errors, mark_fix_result, record_from_output
from app.tools.flash import FlashError, detect_chip_id, flash_elf
from app.tools.serialutil import connect as serial_connect
from app.tools.serialutil import disconnect as serial_disconnect
from app.tools.serialutil import read_available, status as serial_status
from app.tools.hw_session import load_session
from app.tools.validate import inspect_usart, validate_led_task
from app.validation import hardware_status, validate_project


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
            deadline = time.time() + 2.0
            while time.time() < deadline:
                rows = read_available()
                serial_lines = [r.get("text") or "" for r in rows if r.get("text")]
                time.sleep(0.2)
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


def sample_serial(device: str, baud: int = 115200, seconds: float = 2.0) -> dict[str, Any]:
    serial_connect(device, baud)
    try:
        deadline = time.time() + seconds
        lines: list[str] = []
        while time.time() < deadline:
            rows = read_available()
            lines = [r.get("text") or "" for r in rows if r.get("text")]
            time.sleep(0.2)
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
        val = {
            "expected": expect or "USART output",
            "actual": "no serial output after auto-debug",
            "status": "fail",
            "confidence": None,
        }
        extra.append(
            _step(
                "validate",
                "Hardware Validation Failed",
                "failed",
                "Possible Causes: USART 未初始化 / GPIO AF / Baud / Clock",
                reason="still no serial evidence",
            )
        )
    return {
        "available": True,
        "runId": pipeline.get("runId") or f"ad-{uuid.uuid4().hex[:8]}",
        "steps": extra,
        "validation": val,
    }
