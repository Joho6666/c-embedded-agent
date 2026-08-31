from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from app.config.settings import settings
from app.services.llm import LLMError, chat
from app.tools.compiler import CompileError, compile_project
from app.tools.filesystem import list_files, read_file, write_file
from app.tools.knowledge import retrieve_knowledge
from app.tools.search import search_code
from app.workspace.manager import project_root
from app.workspace.paths import PathEscapeError

SYSTEM = """你是一名资深嵌入式 C 工程师。
目标是让 STM32F103C8T6 HAL 工程能够编译链接，而不是只生成看起来合理的代码。
必须参考当前工程源码与编译器真实反馈。
禁止凭空编造寄存器、HAL API、GPIO、头文件，禁止擅自修改 MCU 型号。
不确定时调用 retrieve_knowledge。
可用工具：list_files, read_file, write_file, search_code, compile_project, retrieve_knowledge。
修改文件后必须 compile_project。编译成功即可结束。
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "列出工程文件",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取工程内文件",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "写入工程内文件",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "在工程内搜索字符串",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compile_project",
            "description": "在工程根目录执行 make",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "retrieve_knowledge",
            "description": "检索 STM32 知识库",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
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

    def emit(self, **kwargs: Any) -> None:
        ev = {
            "id": uuid.uuid4().hex[:10],
            "runId": self.id,
            "timestamp": _now(),
            "status": kwargs.get("status", "running"),
            **kwargs,
        }
        self.events.append(ev)
        self.queue.put_nowait(ev)


RUNS: dict[str, AgentRun] = {}


async def event_stream(run_id: str) -> AsyncIterator[str]:
    run = RUNS[run_id]
    idx = 0
    while True:
        while idx < len(run.events):
            yield f"event: agent_event\ndata: {json.dumps(run.events[idx], ensure_ascii=False)}\n\n"
            idx += 1
        item = await run.queue.get()
        if item is None:
            break
        yield f"event: agent_event\ndata: {json.dumps(item, ensure_ascii=False)}\n\n"


def _exec_tool(name: str, args: dict[str, Any], root) -> str:
    if name == "list_files":
        return "\n".join(list_files(root))
    if name == "read_file":
        return read_file(root, str(args.get("path", "")))
    if name == "write_file":
        write_file(root, str(args.get("path", "")), str(args.get("content", "")))
        return "ok"
    if name == "search_code":
        return "\n".join(search_code(root, str(args.get("query", ""))))
    if name == "compile_project":
        result = compile_project(root)
        return json.dumps(result, ensure_ascii=False)
    if name == "retrieve_knowledge":
        hits = retrieve_knowledge(str(args.get("query", "")))
        return json.dumps(hits, ensure_ascii=False)
    return f"unknown tool {name}"


async def run_agent(run: AgentRun) -> None:
    try:
        root = project_root(run.project_id)
    except FileNotFoundError:
        run.emit(type="error", status="failed", title="工程不存在")
        run.status = "failed"
        run.queue.put_nowait(None)
        return

    run.emit(type="plan", status="running", title="分析任务", description=run.prompt)
    try:
        files = list_files(root)
        run.emit(type="reasoning", status="success", title="扫描工程", description=f"{len(files)} 个文件")
    except OSError as e:
        run.emit(type="error", status="failed", title="无法读取工程", description=str(e))
        run.status = "failed"
        run.queue.put_nowait(None)
        return

    try:
        await _llm_loop(run, root)
    except LLMError as e:
        run.emit(type="error", status="failed", title="LLM 不可用", description=str(e))
        run.emit(type="compile", status="running", title="改为直接编译当前工程", tool={"name": "make", "command": "make -j4"})
        await _compile_once(run, root)
    except CompileError as e:
        run.emit(type="compile", status="failed", title="无法编译", description=str(e), output=str(e))
        run.status = "failed"
    except PathEscapeError as e:
        run.emit(type="error", status="failed", title="路径非法", description=str(e))
        run.status = "failed"
    except Exception as e:  # noqa: BLE001
        run.emit(type="error", status="failed", title="Agent 异常", description=str(e))
        run.status = "failed"
    run.queue.put_nowait(None)


async def _compile_once(run: AgentRun, root) -> None:
    try:
        result = compile_project(root)
    except CompileError as e:
        run.emit(type="compile", status="failed", title="无法编译", description=str(e), output=str(e))
        run.status = "failed"
        return
    run.emit(
        type="compile",
        status="success" if result["success"] else "failed",
        title="构建成功" if result["success"] else "构建失败",
        output=result["combined"][-4000:],
        tool={"name": "make", "command": "make -j4", "exitCode": result["exit_code"]},
        diagnostics=[
            {
                "id": f"d{i}",
                "source": "gcc",
                "severity": d["severity"],
                "path": d["file"],
                "line": d["line"],
                "message": d["message"],
            }
            for i, d in enumerate(result["diagnostics"])
        ],
        artifacts=[{"id": a["name"], "runId": run.id, "kind": "elf", "name": a["name"], "createdAt": _now()} for a in result["artifacts"]],
    )
    mem = result.get("memory")
    if result["success"] and mem:
        run.emit(
            type="validation",
            status="success",
            title="构建成功",
            description=f"Flash {mem['flash']} B · RAM {mem['ram']} B",
        )
    run.status = "success" if result["success"] else "failed"


async def _llm_loop(run: AgentRun, root) -> None:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": f"MCU=STM32F103C8T6 Framework=HAL\n任务：{run.prompt}\n工程已存在，请读取文件后修改并编译直到成功。",
        },
    ]
    for i in range(settings.max_agent_iterations):
        run.emit(type="reasoning", status="running", title=f"第 {i + 1} 轮推理")
        data = await chat(messages, TOOLS)
        choice = data["choices"][0]["message"]
        messages.append(choice)
        tool_calls = choice.get("tool_calls") or []
        if not tool_calls:
            text = choice.get("content") or ""
            run.emit(type="reasoning", status="success", title="模型回复", description=text[:500])
            await _compile_once(run, root)
            return
        for tc in tool_calls:
            fn = tc["function"]["name"]
            raw_args = tc["function"].get("arguments") or "{}"
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = {}
            run.emit(type="tool_call", status="running", title=fn, tool={"name": fn, "command": fn})
            if fn == "write_file" and run.mode == "plan":
                result = "plan 模式禁止写文件"
            else:
                result = _exec_tool(fn, args, root)
            if fn == "write_file" and run.mode != "plan":
                path = str(args.get("path", ""))
                run.emit(
                    type="file_diff",
                    status="success",
                    title="写入文件",
                    files=[path if path.startswith("/") else f"/{path}"],
                    proposed=str(args.get("content", ""))[:8000],
                    original="",
                )
            if fn == "retrieve_knowledge":
                run.emit(type="knowledge_result", status="success", title="知识检索", description=result[:800])
            if fn == "compile_project":
                try:
                    parsed = json.loads(result)
                except json.JSONDecodeError:
                    parsed = {"success": False, "combined": result, "diagnostics": [], "exit_code": 1, "artifacts": []}
                run.emit(
                    type="compile",
                    status="success" if parsed.get("success") else "failed",
                    title="构建成功" if parsed.get("success") else "构建失败",
                    output=str(parsed.get("combined", ""))[-4000:],
                    tool={"name": "make", "command": "make -j4", "exitCode": parsed.get("exit_code", 1)},
                    diagnostics=[
                        {
                            "id": f"d{i}",
                            "source": "gcc",
                            "severity": d.get("severity", "error"),
                            "path": d.get("file", ""),
                            "line": d.get("line", 0),
                            "message": d.get("message", ""),
                        }
                        for i, d in enumerate(parsed.get("diagnostics") or [])
                    ],
                )
                if parsed.get("success"):
                    mem = parsed.get("memory") or {}
                    run.emit(
                        type="validation",
                        status="success",
                        title="构建成功",
                        description=f"Flash {mem.get('flash', '?')} B · RAM {mem.get('ram', '?')} B",
                    )
                    run.status = "success"
                    return
            messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": result[:8000]})
    run.emit(type="error", status="failed", title="达到最大迭代次数")
    run.status = "failed"
