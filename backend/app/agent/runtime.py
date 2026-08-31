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
from app.tools.patch import PatchError, apply_patch
from app.tools.search import search_code
from app.tools.validate import validate_led_task
from app.workspace.manager import project_root
from app.workspace.paths import PathEscapeError, ProtectedPathError

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
    return f"unknown tool {name}"


async def _write_with_diff(run: AgentRun, root: Path, path: str, content: str) -> str:
    if run.cancelled():
        return "RUN_STOPPED"
    before = ""
    try:
        before = read_file(root, path)
    except FileNotFoundError:
        before = ""
    write_file(root, path, content, advanced=run.advanced)
    run.emit(
        type="file_diff",
        status="success" if run.mode == "auto" else "waiting_approval",
        title="写入文件",
        files=[path if path.startswith("/") else f"/{path}"],
        original=before[:8000],
        proposed=content[:8000],
        path=path,
        before=before[:8000],
        after=content[:8000],
        requiresApproval=run.mode == "code",
    )
    save_file_change(run.id, path, before, content)
    return "ok"


async def _patch_with_diff(run: AgentRun, root: Path, path: str, patch: str) -> str:
    if run.cancelled():
        return "RUN_STOPPED"
    before = read_file(root, path)
    try:
        after = apply_patch(root, path, patch, advanced=run.advanced)
    except PatchError as e:
        return str(e)
    run.emit(
        type="file_diff",
        status="success" if run.mode == "auto" else "waiting_approval",
        title="应用补丁",
        files=[path if path.startswith("/") else f"/{path}"],
        original=before[:8000],
        proposed=after[:8000],
        path=path,
        before=before[:8000],
        after=after[:8000],
        requiresApproval=run.mode == "code",
    )
    save_file_change(run.id, path, before, after)
    return "ok"


async def _compile(run: AgentRun, root: Path) -> dict[str, Any]:
    async def on_line(stream: str, line: str) -> None:
        run.emit(type="terminal", status="running", title="make", stream=stream, content=line, output=line)

    result = await compile_project_streaming(root, on_line)
    run.last_errors = [d for d in result.get("diagnostics") or [] if d.get("severity") == "error"]
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
        led = validate_led_task(root, "PC13")
        run.emit(
            type="validation",
            status="success" if led["passed"] else "failed",
            title=f"LED 校验 {led['score']}",
            description=json.dumps(led["checks"], ensure_ascii=False),
        )
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
    ctx = build_context(root, iteration=0, board=board.get("board", "Blue Pill"))
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": f"{context_prompt(ctx)}\n任务：{run.prompt}\n工程已存在。先读文件，再最小修改并编译直到 exit code == 0。",
        },
    ]
    if looks_complex(run.prompt):
        run.emit(type="reasoning", status="success", title="复杂任务，已生成 Plan")

    for i in range(settings.max_agent_iterations):
        if run.cancelled():
            raise asyncio.CancelledError()
        run.iteration = i + 1
        ctx = build_context(root, iteration=i + 1, errors=run.last_errors, knowledge=run.citations[-3:], board=board.get("board", "Blue Pill"))
        messages.append({"role": "system", "content": "当前上下文：\n" + context_prompt(ctx)})
        run.emit(type="reasoning", status="running", title=f"第 {i + 1} 轮推理")
        t0 = time.perf_counter()
        data = await chat(messages, TOOLS)
        latency = int((time.perf_counter() - t0) * 1000)
        choice = data["choices"][0]["message"]
        messages.append(choice)
        tool_calls = choice.get("tool_calls") or []
        save_model_call(run.id, settings.llm_model, data.get("usage"), latency, len(tool_calls))
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
                result = json.dumps(compiled, ensure_ascii=False)
                if compiled.get("success"):
                    run.status = "success"
                    return
            else:
                result = _exec_sync(fn, args, root, run)
                if fn == "retrieve_knowledge":
                    run.emit(type="knowledge_result", status="success", title="知识检索", description=result[:800])
            messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": str(result)[:8000]})
    run.emit(type="error", status="failed", title="达到最大迭代次数")
    run.status = "failed"
