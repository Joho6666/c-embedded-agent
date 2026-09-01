from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator

from app.agent.context import build_context, context_prompt
from app.agent.planner import looks_complex, make_plan
from app.config.settings import settings
from app.db import finish_run, save_build, save_event, save_file_change, save_model_call, save_run
from app.mcu.stm32f103 import get_mcu_info, get_pin_info, load_board
from app.services.llm import LLMError, chat
from app.tools.analysis import clangd_diagnostics, cppcheck_project
from app.tools.compiler import CompileError, compile_project_streaming
from app.tools.filesystem import list_files, read_file, write_file
from app.tools.gitutil import snapshot
from app.tools.knowledge import format_citation, retrieve_knowledge
from app.tools.patch import PatchError, apply_patch, preview_patch
from app.tools.search import search_code
from app.tools.error_memory import apply_known_fix, list_errors, mark_fix_result, record_from_output, match_known_errors
from app.tools.flash import FlashError, flash_elf
from app.tools.hardware_run import run_pipeline, sample_serial
from app.tools.skills import get_skill, skill_summary
from app.tools.hal_modules import register_hal_module
from app.tools.periph_gen import configure_peripheral
from app.tools.validate import inspect_usart, validate_led_task
from app.validation import validate_project
from app.workspace.manager import project_root
from app.workspace.paths import PathEscapeError, ProtectedPathError
from app.agent.context import led_from_ioc, load_ioc_analysis

SYSTEM = """你是一名资深嵌入式 C 工程师，目标是让 STM32F103C8T6 HAL 工程真实编译链接。
规则：
1. 先读工程，不要先写代码。
2. 不知道 API 就 retrieve_knowledge。
3. 不知道 Pin 就 get_pin_info / get_mcu_info。
4. 修改最少文件；优先 apply_patch，不要整文件覆盖。
5. 不要修改 Drivers、startup、链接脚本、Makefile，除非用户处于 advanced 模式。
6. 优先修改 Core/Src 和 Core/Inc。
7. 每次修改后 compile_project。
8. 根据真实 GCC/LD Error 修复。
9. Build 成功以后可以参考静态分析，但不能把分析失败当成编译失败。
10. 不允许声称成功，除非 compiler exit code == 0。
禁止凭空编造寄存器、HAL API、GPIO、头文件，禁止擅自修改 MCU 型号。
Blue Pill 板载 LED 默认 PC13，不是 PA5。
USART1 默认 PA9 TX / PA10 RX。
"""

TOOLS = [
    {"type": "function", "function": {"name": "list_files", "description": "列出工程文件", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "read_file", "description": "读取工程内文件", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "写入工程内文件（整文件）。优先用 apply_patch。", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "apply_patch", "description": "对工程文件应用 unified diff", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "patch": {"type": "string"}}, "required": ["path", "patch"]}}},
    {"type": "function", "function": {"name": "search_code", "description": "在工程内搜索字符串", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "compile_project", "description": "在工程根目录执行 make", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "retrieve_knowledge", "description": "检索 STM32 知识库", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "get_mcu_info", "description": "STM32F103C8T6 结构化信息", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "get_pin_info", "description": "查询引脚复用", "parameters": {"type": "object", "properties": {"pin": {"type": "string"}}, "required": ["pin"]}}},
    {"type": "function", "function": {"name": "flash_firmware", "description": "用 OpenOCD ST-Link 烧录 firmware.elf。无调试器时返回失败，不要假装成功。", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "serial_read", "description": "打开串口采样约 2 秒。baud 仅 9600 或 115200。", "parameters": {"type": "object", "properties": {"device": {"type": "string"}, "baud": {"type": "integer"}, "expect": {"type": "string"}}, "required": ["device"]}}},
    {"type": "function", "function": {"name": "run_on_device", "description": "Build→Flash→Serial→Validate。无板/无串口标 unavailable。", "parameters": {"type": "object", "properties": {"device": {"type": "string"}, "baud": {"type": "integer"}, "expect": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "load_skill", "description": "加载外设 Skill 摘要（USART/DMA/TIM…）", "parameters": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}}},
    {"type": "function", "function": {"name": "search_error_memory", "description": "搜索已知编译/链接错误修复", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "tag": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "apply_error_memory_fix", "description": "仅应用已知机械修复（Makefile HAL source / IRQ stub）。未知错误不要调用。", "parameters": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}}},
    {"type": "function", "function": {"name": "register_hal_module", "description": "安全登记 HAL 模块到 Makefile + stm32f1xx_hal_conf.h，去重。不要手改 Makefile。", "parameters": {"type": "object", "properties": {"module": {"type": "string"}}, "required": ["module"]}}},
    {"type": "function", "function": {"name": "configure_usart", "description": "按 Golden Recipe 生成 USART 初始化（Core/Src/usart.c）。LLM 只写业务逻辑。", "parameters": {"type": "object", "properties": {"instance": {"type": "string"}, "baud": {"type": "integer"}, "mode": {"type": "string"}}, "required": ["instance"]}}},
    {"type": "function", "function": {"name": "configure_adc", "description": "按 Golden Recipe 生成 ADC 初始化。", "parameters": {"type": "object", "properties": {"instance": {"type": "string"}, "channel": {"type": "integer"}, "mode": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "configure_pwm", "description": "按 Golden Recipe 生成 TIM PWM 初始化。", "parameters": {"type": "object", "properties": {"instance": {"type": "string"}, "channel": {"type": "integer"}}}}},
    {"type": "function", "function": {"name": "configure_i2c", "description": "按 Golden Recipe 生成 I2C 初始化。", "parameters": {"type": "object", "properties": {"instance": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "configure_spi", "description": "按 Golden Recipe 生成 SPI 初始化。", "parameters": {"type": "object", "properties": {"instance": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "configure_exti", "description": "按 Golden Recipe 生成 EXTI GPIO 中断初始化。", "parameters": {"type": "object", "properties": {"pin": {"type": "string"}, "edge": {"type": "string"}}}}},
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AgentRun:
    def __init__(self, run_id: str, project_id: str, prompt: str, mode: str) -> None:
        self.id = run_id
        self.project_id = project_id
        self.prompt = prompt
        self.mode = mode
        self.events: list[dict[str, Any]] = []
        self.queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        self.status = "running"
        self.task: asyncio.Task[None] | None = None
        self.cancel_event = asyncio.Event()
        self.iteration = 0
        self.last_errors: list[dict[str, Any]] = []
        self.citations: list[dict[str, Any]] = []
        self.snapshot_sha = ""
        self.advanced = mode == "advanced"
        self.approval_event = asyncio.Event()
        self.approval_decision = "approved"
        self.always_approve = False
        self.pending_approval_id: str | None = None
        self.serial_device: str | None = None
        self.serial_baud = 115200
        self.expect: str | None = None
        self.loaded_skills: list[dict[str, Any]] = []
        self.input_tokens = 0
        self.output_tokens = 0
        self.latency_ms = 0

    def cancelled(self) -> bool:
        return self.cancel_event.is_set() or self.status == "cancelled"

    def emit(self, **kwargs: Any) -> None:
        if self.cancelled() and kwargs.get("type") not in {"run_stopped", "error"}:
            return
        ev = {
            "id": uuid.uuid4().hex[:10],
            "runId": self.id,
            "timestamp": _now(),
            "status": kwargs.get("status", "running"),
            **kwargs,
        }
        self.events.append(ev)
        self.queue.put_nowait(ev)
        try:
            save_event(ev)
        except Exception:
            pass


RUNS: dict[str, AgentRun] = {}


async def event_stream(run_id: str) -> AsyncIterator[str]:
    run = RUNS[run_id]
    while True:
        item = await run.queue.get()
        if item is None:
            break
        yield f"event: agent_event\ndata: {json.dumps(item, ensure_ascii=False)}\n\n"


async def request_stop(run: AgentRun) -> None:
    run.cancel_event.set()
    run.approval_decision = "rejected"
    run.approval_event.set()
    run.status = "cancelled"
    if run.task and not run.task.done():
        run.task.cancel()
        try:
            await run.task
        except asyncio.CancelledError:
            pass
    run.emit(type="run_stopped", status="cancelled", title="已停止")
    run.queue.put_nowait(None)
    finish_run(run.id, "cancelled", run.iteration)


def resolve_approval(run: AgentRun, decision: str, approval_id: str | None = None) -> None:
    if approval_id and run.pending_approval_id and approval_id != run.pending_approval_id:
        return
    raw = decision if decision in {"approved", "rejected", "once", "always"} else "rejected"
    if raw == "always":
        run.always_approve = True
        run.approval_decision = "approved"
    elif raw == "once":
        run.approval_decision = "approved"
    else:
        run.approval_decision = raw
    run.approval_event.set()


def _exec_sync(name: str, args: dict[str, Any], root: Path, run: AgentRun) -> str:
    if name == "list_files":
        return "\n".join(list_files(root))
    if name == "read_file":
        return read_file(root, str(args.get("path", "")))
    if name == "search_code":
        return "\n".join(search_code(root, str(args.get("query", ""))))
    if name == "retrieve_knowledge":
        hits = retrieve_knowledge(str(args.get("query", "")))
        run.citations.extend(hits)
        return json.dumps(hits, ensure_ascii=False)
    if name == "get_mcu_info":
        return json.dumps(get_mcu_info(), ensure_ascii=False)
    if name == "get_pin_info":
        return json.dumps(get_pin_info(str(args.get("pin", ""))), ensure_ascii=False)
    if name == "load_skill":
        item = get_skill(str(args.get("id", "")))
        if not item:
            return json.dumps({"available": False, "reason": "skill not found"})
        run.loaded_skills.append(item)
        run.emit(type="tool_call", status="success", title=f"Load Skill {item.get('name')}", description=json.dumps(skill_summary(item), ensure_ascii=False)[:800])
        return json.dumps(skill_summary(item), ensure_ascii=False)
    if name == "search_error_memory":
        hits = list_errors(str(args.get("query", "")), str(args.get("tag", "") or ""))
        run.emit(
            type="tool_call",
            status="success" if hits else "failed",
            title="Searching Error Memory",
            description=json.dumps([{"id": h["id"], "pattern": h["pattern"]} for h in hits[:5]], ensure_ascii=False),
        )
        return json.dumps(hits[:8], ensure_ascii=False)
    if name == "apply_error_memory_fix":
        eid = str(args.get("id", ""))
        fix = apply_known_fix(root, eid)
        run.emit(
            type="file_diff" if fix.get("applied") else "tool_call",
            status="success" if fix.get("applied") else "failed",
            title=f"Apply Fix {eid}",
            files=fix.get("files") or [],
            description=json.dumps(fix, ensure_ascii=False)[:800],
        )
        return json.dumps(fix, ensure_ascii=False)
    if name == "register_hal_module":
        out = register_hal_module(root, str(args.get("module", "")))
        run.emit(
            type="tool_call",
            status="success" if out.get("ok") else "failed",
            title=f"register_hal_module {args.get('module')}",
            description=json.dumps(out, ensure_ascii=False)[:800],
        )
        return json.dumps(out, ensure_ascii=False)
    if name.startswith("configure_"):
        kind = name.replace("configure_", "")
        out = configure_peripheral(root, kind, args)
        run.emit(
            type="tool_call",
            status="success" if out.get("ok") else "failed",
            title=name,
            files=out.get("files") or [],
            description=json.dumps(out, ensure_ascii=False)[:800],
        )
        return json.dumps(out, ensure_ascii=False)
    return f"unknown tool {name}"


async def _await_approval(run: AgentRun, approval_id: str) -> str:
    if run.always_approve:
        return "approved"
    run.pending_approval_id = approval_id
    run.approval_event.clear()
    run.approval_decision = "pending"
    try:
        await asyncio.wait_for(run.approval_event.wait(), timeout=3600)
    except TimeoutError:
        run.pending_approval_id = None
        return "rejected"
    run.pending_approval_id = None
    if run.cancelled():
        return "RUN_STOPPED"
    return run.approval_decision


async def _write_with_diff(run: AgentRun, root: Path, path: str, content: str) -> str:
    if run.cancelled():
        return "RUN_STOPPED"
    before = ""
    try:
        before = read_file(root, path)
    except FileNotFoundError:
        before = ""
    approval_id = uuid.uuid4().hex[:10]
    gated = run.mode == "code"
    run.emit(
        type="file_diff",
        status="waiting_approval" if gated else "success",
        title="写入文件",
        files=[path if path.startswith("/") else f"/{path}"],
        original=before[:8000],
        proposed=content[:8000],
        path=path,
        before=before[:8000],
        after=content[:8000],
        requiresApproval=gated,
        approvalId=approval_id if gated else None,
    )
    if gated:
        decision = await _await_approval(run, approval_id)
        if decision in {"rejected", "RUN_STOPPED", "pending"}:
            return "rejected" if decision != "RUN_STOPPED" else decision
    write_file(root, path, content, advanced=run.advanced)
    save_file_change(run.id, path, before, content)
    return "ok"


async def _patch_with_diff(run: AgentRun, root: Path, path: str, patch: str) -> str:
    if run.cancelled():
        return "RUN_STOPPED"
    before = read_file(root, path)
    try:
        proposed = preview_patch(before, patch)
    except PatchError as e:
        return str(e)
    gated = run.mode == "code"
    approval_id = uuid.uuid4().hex[:10]
    run.emit(
        type="file_diff",
        status="waiting_approval" if gated else "success",
        title="应用补丁",
        files=[path if path.startswith("/") else f"/{path}"],
        original=before[:8000],
        proposed=proposed[:8000],
        path=path,
        before=before[:8000],
        after=proposed[:8000],
        requiresApproval=gated,
        approvalId=approval_id if gated else None,
    )
    if gated:
        decision = await _await_approval(run, approval_id)
        if decision in {"rejected", "RUN_STOPPED", "pending"}:
            return "rejected" if decision != "RUN_STOPPED" else decision
    try:
        after = apply_patch(root, path, patch, advanced=run.advanced)
    except PatchError as e:
        return str(e)
    save_file_change(run.id, path, before, after)
    return "ok"


async def _apply_known_fixes(run: AgentRun, root: Path, compiled: dict[str, Any]) -> dict[str, Any]:
    """Deterministic Error Memory: known signature → fix → rebuild. Unknown errors stay for the LLM."""
    text = str(compiled.get("combined") or "")
    hits = match_known_errors(text)
    applied = False
    for hit in hits:
        if not hit.get("mechanical"):
            continue
        fix = apply_known_fix(root, hit["id"])
        run.emit(
            type="tool_call",
            status="success" if fix.get("applied") else "failed",
            title=f"Known Fix {hit['id']}",
            description=json.dumps(fix, ensure_ascii=False)[:800],
        )
        if fix.get("applied"):
            applied = True
            compiled = await _compile(run, root)
            mark_fix_result(hit["id"], success=bool(compiled.get("success")))
            if compiled.get("success"):
                return compiled
    return compiled if applied else compiled


async def _compile(run: AgentRun, root: Path) -> dict[str, Any]:
    async def on_line(stream: str, line: str) -> None:
        run.emit(type="terminal", status="running", title="make", stream=stream, content=line, output=line)

    result = await compile_project_streaming(root, on_line)
    combined = str(result.get("combined") or "")
    hits = record_from_output(combined, success=bool(result.get("success")))
    run.last_errors = [d for d in result.get("diagnostics") or [] if d.get("severity") == "error"]
    if not result.get("success") and hits:
        memories = [list_errors(eid) for eid in hits]
        flat = [m for group in memories for m in group]
        run.emit(
            type="tool_call",
            status="success",
            title="Memory Match",
            description=json.dumps([{"id": h, "pattern": (flat[0]["pattern"] if flat else h)} for h in hits], ensure_ascii=False),
        )
        for h in hits:
            run.last_errors.append({"source": "memory", "file": "", "line": 0, "severity": "error", "message": f"error memory {h}"})
    diags = [
        {
            "id": f"d{i}",
            "source": d.get("source", "gcc"),
            "severity": d.get("severity", "error"),
            "path": d.get("file", ""),
            "line": d.get("line", 0),
            "message": d.get("message", ""),
        }
        for i, d in enumerate(result.get("diagnostics") or [])
    ]
    arts = [
        {"id": a["name"], "runId": run.id, "kind": a["name"].rsplit(".", 1)[-1], "name": a["name"], "createdAt": _now()}
        for a in result.get("artifacts") or []
    ]
    run.emit(
        type="compile",
        status="success" if result["success"] else "failed",
        title="构建成功" if result["success"] else "构建失败",
        output=result["combined"][-4000:],
        tool={"name": "make", "command": "make -j4", "exitCode": result["exit_code"]},
        diagnostics=diags,
        artifacts=arts,
    )
    save_build(run.id, run.project_id, result)
    if result["success"]:
        mem = result.get("memory") or {}
        run.emit(
            type="build_result",
            status="success",
            title="构建成功",
            description=f"Flash {mem.get('flash', '?')} B · RAM {mem.get('ram', '?')} B",
            artifacts=arts,
        )
        ioc = load_ioc_analysis(root)
        pin = led_from_ioc(ioc)
        led = validate_led_task(root, pin)
        usart = inspect_usart(root)
        semantic = validate_project(root, run.prompt)
        run.emit(
            type="validation",
            status="success" if semantic.get("passed") or led["passed"] else "failed",
            title=f"静态校验 score={semantic.get('score', led['score'])} pin={pin}",
            description=json.dumps(
                {
                    "method": "static_source",
                    "led": led["checks"],
                    "usart": usart.get("checks"),
                    "semantic": semantic,
                },
                ensure_ascii=False,
            ),
        )
        if _wants_device(run.prompt):
            await _maybe_run_on_device(run, root)
        clang = clangd_diagnostics(root)
        if clang.get("available") and clang.get("diagnostics"):
            run.emit(type="diagnostic", status="success", title="clangd", description=str(clang["diagnostics"][:8]))
        elif not clang.get("available"):
            run.emit(type="diagnostic", status="success", title="clangd Unavailable")
        cpp = cppcheck_project(root)
        if cpp.get("available") and cpp.get("diagnostics"):
            run.emit(type="test", status="success", title="cppcheck", description=str(cpp["diagnostics"][:8]))
        elif not cpp.get("available"):
            run.emit(type="test", status="success", title="cppcheck Unavailable")
    return result


def _wants_device(prompt: str) -> bool:
    p = prompt.lower()
    return any(k in p for k in ("usart", "uart", "串口", "hello", "flash", "真机", "500ms", "run on device"))


def _emit_pipeline(run: AgentRun, pipeline: dict[str, Any]) -> None:
    for step in pipeline.get("steps") or []:
        kind = step.get("kind") or "tool_call"
        ev_type = {"flash": "flash", "serial": "serial", "validate": "validation", "build": "compile"}.get(kind, "tool_call")
        logs = step.get("logs") or ""
        if ev_type == "serial" and logs:
            for i, line in enumerate(logs.splitlines()[:40]):
                run.emit(type="serial", status=step.get("status") or "running", title="Serial", output=f"[00:00.{i}] {line}")
        else:
            run.emit(
                type=ev_type,
                status="success" if step.get("status") == "success" else ("failed" if step.get("status") == "failed" else "failed"),
                title=step.get("title") or kind,
                description=step.get("detail"),
                output=logs[-2000:] if logs else None,
                reason=step.get("reason"),
            )
    val = pipeline.get("validation") or {}
    if val:
        run.emit(
            type="validation",
            status="success" if val.get("status") == "pass" else ("failed" if val.get("status") == "fail" else "failed"),
            title="Hardware validation",
            description=json.dumps(
                {
                    "method": "serial" if val.get("actual") else "unavailable",
                    "expected": val.get("expected"),
                    "observed": val.get("actual"),
                    "confidence": val.get("confidence"),
                    "status": val.get("status"),
                },
                ensure_ascii=False,
            ),
        )


async def _maybe_run_on_device(run: AgentRun, root: Path) -> None:
    device = run.serial_device
    pipeline = run_pipeline(root, serial_device=device, baud=run.serial_baud, expect=run.expect)
    _emit_pipeline(run, pipeline)


async def _flash_tool(run: AgentRun, root: Path) -> str:
    try:
        data = flash_elf(root)
    except FlashError as e:
        run.emit(type="flash", status="failed", title="Flash", description=str(e))
        return json.dumps({"success": False, "error": str(e)})
    ok = bool(data.get("success"))
    run.emit(type="flash", status="success" if ok else "failed", title="Flash", output=str(data.get("output") or "")[-2000:])
    return json.dumps(data, ensure_ascii=False)[:8000]


async def _serial_tool(run: AgentRun, args: dict[str, Any]) -> str:
    device = str(args.get("device") or run.serial_device or "")
    baud = int(args.get("baud") or run.serial_baud or 115200)
    if not device:
        run.emit(type="serial", status="failed", title="Serial", description="no serial device")
        return json.dumps({"available": False, "reason": "no serial device"})
    try:
        sample = sample_serial(device, baud)
    except (ValueError, RuntimeError, OSError) as e:
        run.emit(type="serial", status="failed", title="Serial", description=str(e))
        return json.dumps({"success": False, "error": str(e)})
    lines = sample.get("lines") or []
    for i, line in enumerate(lines[:40]):
        run.emit(type="serial", status="success", title="Serial", output=f"[00:00.{i}] {line}")
    if not lines:
        run.emit(type="serial", status="failed", title="Serial", description="no serial output")
    return json.dumps(sample, ensure_ascii=False)[:8000]


async def run_agent(run: AgentRun) -> None:
    try:
        save_run(run.id, run.project_id, run.prompt, "running", settings.llm_model)
        try:
            root = project_root(run.project_id)
        except FileNotFoundError:
            run.emit(type="error", status="failed", title="工程不存在")
            run.status = "failed"
            run.queue.put_nowait(None)
            finish_run(run.id, "failed")
            return

        try:
            run.snapshot_sha = snapshot(root, f"pre-run {run.id}")
        except Exception:
            run.snapshot_sha = ""

        board = load_board(settings.repo_root)
        plan = make_plan(run.prompt)
        run.emit(
            type="plan",
            status="running",
            title="任务计划",
            description="\n".join(f"{s['index']}. {s['title']}" for s in plan),
            plan=plan,
        )
        try:
            files = list_files(root)
            run.emit(type="reasoning", status="success", title="扫描工程", description=f"{len(files)} 个文件 · LED={board.get('led', 'PC13')}")
        except OSError as e:
            run.emit(type="error", status="failed", title="无法读取工程", description=str(e))
            run.status = "failed"
            run.queue.put_nowait(None)
            finish_run(run.id, "failed")
            return

        try:
            await _llm_loop(run, root, board)
        except asyncio.CancelledError:
            run.status = "cancelled"
            raise
        except LLMError as e:
            run.emit(type="error", status="failed", title="LLM 不可用", description=str(e))
            run.emit(type="compile", status="running", title="改为直接编译当前工程", tool={"name": "make", "command": "make -j4"})
            await _compile(run, root)
            run.status = "success" if run.status != "cancelled" and run.events and run.events[-1].get("status") == "success" else run.status
            if run.status == "running":
                run.status = "failed"
        except CompileError as e:
            run.emit(type="compile", status="failed", title="无法编译", description=str(e), output=str(e))
            run.status = "failed"
        except PathEscapeError as e:
            run.emit(type="error", status="failed", title="路径非法", description=str(e))
            run.status = "failed"
        except ProtectedPathError as e:
            run.emit(type="error", status="failed", title="受保护文件", description=str(e))
            run.status = "failed"
        except Exception as e:  # noqa: BLE001
            run.emit(type="error", status="failed", title="Agent 异常", description=str(e))
            run.status = "failed"
        if run.citations:
            run.emit(
                type="knowledge_result",
                status="success",
                title="Knowledge Used",
                description="\n".join(format_citation(c) for c in run.citations[:8]),
                source={
                    "title": run.citations[0].get("source") or run.citations[0].get("title"),
                    "section": run.citations[0].get("section"),
                    "page": int(run.citations[0]["page"]) if str(run.citations[0].get("page") or "").isdigit() else None,
                },
            )
        finish_run(run.id, run.status, run.iteration)
    except asyncio.CancelledError:
        run.status = "cancelled"
        finish_run(run.id, "cancelled", run.iteration)
        raise
    finally:
        if not run.cancel_event.is_set():
            run.queue.put_nowait(None)


async def _llm_loop(run: AgentRun, root: Path, board: dict[str, Any]) -> None:
    ctx = build_context(
        root,
        iteration=0,
        board=board.get("board", "Blue Pill"),
        prompt=run.prompt,
        extra_skills=run.loaded_skills,
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": f"{context_prompt(ctx)}\n任务：{run.prompt}\n工程已存在。先读文件，再最小修改并编译直到 exit code == 0。"
            f"{' 编译成功后可用 run_on_device / flash_firmware / serial_read。无调试器时不要声称烧录成功。' if _wants_device(run.prompt) else ''}",
        },
    ]
    if looks_complex(run.prompt):
        run.emit(type="reasoning", status="success", title="复杂任务，已生成 Plan")

    for i in range(settings.max_agent_iterations):
        if run.cancelled():
            raise asyncio.CancelledError()
        run.iteration = i + 1
        ctx = build_context(
            root,
            iteration=i + 1,
            errors=run.last_errors,
            knowledge=run.citations[-3:],
            board=board.get("board", "Blue Pill"),
            prompt=run.prompt,
            extra_skills=run.loaded_skills,
        )
        messages.append({"role": "system", "content": "当前上下文：\n" + context_prompt(ctx)})
        run.emit(type="reasoning", status="running", title=f"第 {i + 1} 轮推理")
        t0 = time.perf_counter()
        data = await chat(messages, TOOLS)
        latency = int((time.perf_counter() - t0) * 1000)
        choice = data["choices"][0]["message"]
        messages.append(choice)
        tool_calls = choice.get("tool_calls") or []
        usage = data.get("usage") or {}
        run.input_tokens += int(usage.get("prompt_tokens") or 0)
        run.output_tokens += int(usage.get("completion_tokens") or 0)
        run.latency_ms += latency
        save_model_call(run.id, settings.llm_model, usage, latency, len(tool_calls))
        if not tool_calls:
            text = choice.get("content") or ""
            run.emit(type="reasoning", status="success", title="模型回复", description=text[:500])
            result = await _compile(run, root)
            run.status = "success" if result.get("success") else "failed"
            return
        for tc in tool_calls:
            if run.cancelled():
                raise asyncio.CancelledError()
            fn = tc["function"]["name"]
            raw_args = tc["function"].get("arguments") or "{}"
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = {}
            run.emit(type="tool_call", status="running", title=fn, tool={"name": fn, "command": fn})
            if run.mode == "plan" and fn in {"write_file", "apply_patch"}:
                result = "plan 模式禁止写文件"
            elif fn == "write_file":
                try:
                    result = await _write_with_diff(run, root, str(args.get("path", "")), str(args.get("content", "")))
                except ProtectedPathError as e:
                    result = f"PROTECTED: {e}"
            elif fn == "apply_patch":
                try:
                    result = await _patch_with_diff(run, root, str(args.get("path", "")), str(args.get("patch", "")))
                except (ProtectedPathError, FileNotFoundError) as e:
                    result = f"PATCH_FAILED: {e}"
            elif fn == "compile_project":
                compiled = await _compile(run, root)
                if not compiled.get("success"):
                    compiled = await _apply_known_fixes(run, root, compiled)
                result = json.dumps(compiled, ensure_ascii=False)
                if compiled.get("success") and not _wants_device(run.prompt):
                    run.status = "success"
                    return
            elif fn == "flash_firmware":
                result = await _flash_tool(run, root)
            elif fn == "serial_read":
                result = await _serial_tool(run, args)
            elif fn == "run_on_device":
                if args.get("device"):
                    run.serial_device = str(args.get("device"))
                if args.get("baud"):
                    run.serial_baud = int(args.get("baud"))
                if args.get("expect"):
                    run.expect = str(args.get("expect"))
                pipeline = run_pipeline(root, serial_device=run.serial_device, baud=run.serial_baud, expect=run.expect)
                _emit_pipeline(run, pipeline)
                result = json.dumps(pipeline, ensure_ascii=False)[:8000]
            elif fn == "apply_error_memory_fix":
                result = _exec_sync(fn, args, root, run)
                compiled = await _compile(run, root)
                eid = str(args.get("id", ""))
                if eid:
                    mark_fix_result(eid, success=bool(compiled.get("success")))
                result = json.dumps({"fix": json.loads(result) if result.startswith("{") else result, "compile": compiled.get("success")}, ensure_ascii=False)[:8000]
            else:
                result = _exec_sync(fn, args, root, run)
                if fn == "retrieve_knowledge":
                    run.emit(type="knowledge_result", status="success", title="知识检索", description=result[:800])
            messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": str(result)[:8000]})
    run.emit(type="error", status="failed", title="达到最大迭代次数")
    run.status = "failed"
