#!/usr/bin/env python3
"""Watch the cea-embedded MCP plugin work, from the point of view of an agent harness.

Starts the plugin over MCP stdio (exactly how Claude Code / Codex / Cursor launch it),
then walks through: doctor -> one-click flash -> live state -> behaviour check that
catches a "compiles but wrong" bug -> fix -> pass. Uses the virtual Blue Pill.

    python scripts/demo_plugin.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = Path(__file__).resolve().parents[1]
LAUNCHER = REPO / "scripts" / "cea_mcp.py"
GOLDEN = REPO / "examples" / "golden"
IGNORE = shutil.ignore_patterns("*.o", "*.d", "*.elf", "*.hex", "*.bin", "*.map")

B, G, R, Y, C, D, X = "\033[1m", "\033[32m", "\033[31m", "\033[33m", "\033[36m", "\033[2m", "\033[0m"


def step(n: int, title: str) -> None:
    print(f"\n{B}{C}━━ 第 {n} 步 · {title} {'━' * max(4, 40 - len(title))}{X}")


def call_line(tool: str, args: dict) -> None:
    shown = ", ".join(f"{k}={v!r}" for k, v in args.items() if k != "project")
    print(f"{D}AI → cea/{tool}({shown}){X}")


def ok(flag: bool) -> str:
    return f"{G}✔{X}" if flag else f"{R}✘{X}"


async def call(session: ClientSession, tool: str, args: dict | None = None) -> dict:
    args = args or {}
    call_line(tool, args)
    t0 = time.perf_counter()
    result = await session.call_tool(tool, args)
    data = json.loads(result.content[0].text)
    print(f"{D}   ({time.perf_counter() - t0:.1f}s){X}")
    return data


async def demo() -> None:
    work = Path(tempfile.mkdtemp(prefix="cea-demo-"))
    usart = shutil.copytree(GOLDEN / "stm32f103_usart", work / "usart_hello", ignore=IGNORE)
    led = shutil.copytree(GOLDEN / "stm32f103_led", work / "led_blink", ignore=IGNORE)

    params = StdioServerParameters(command=sys.executable, args=[str(LAUNCHER)], env={**os.environ, "CEA_DEVICE": "virtual"})
    print(f"{B}cea-embedded 插件演示{X}  （本脚本扮演 Claude Code / Codex 这类 AI 助手，通过 MCP 调用插件）")
    print(f"{D}演示工程复制在 {work}{X}")

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = [t.name for t in (await session.list_tools()).tools]
            print(f"已连接插件，提供 {len(tools)} 个工具：{', '.join(tools)}")

            step(1, "体检环境 doctor")
            d = await call(session, "doctor")
            print(f"  ARM GCC {ok(bool(d['arm_gcc']))}   make {ok(bool(d['make']))}   Renode {ok(bool(d['renode']))}   "
                  f"OpenOCD {ok(bool(d['openocd']))}")
            print(f"  当前板子：{B}{d['backend']['board']}{X}  证据类型 {Y}{d['backend']['evidence']}{X}")

            step(2, "一键烧录：串口打印 Hello 的工程")
            print(f"  {D}首次会启动虚拟板（约 20 秒）…{X}")
            f = await call(session, "flash", {"project": str(usart), "expect": "Hello", "observe_seconds": 1.6})
            mem = f["build"]["memory"] or {}
            print(f"  编译 {ok(f['build']['success'])}  Flash {mem.get('flash_bytes')} B / RAM {mem.get('ram_bytes')} B  "
                  f"警告 {f['build']['warnings']}")
            print(f"  烧录后 1.6 秒内串口输出：{f['serial']}")
            print(f"  期望看到 'Hello'：{ok(bool(f['expect_found']))}   证据 {Y}{f['evidence']}{X}")

            step(3, "板子在后台持续运行 · 看最新状态")
            await anyio.sleep(4)
            s = await call(session, "status", {"pins": ["PC13"]})
            dev, lf = s["device"], s["last_flash"]
            pc13 = s["pins"]["PC13"]
            print(f"  板上固件 sha {lf['sha256_12']}  运行中 {ok(dev['running'])}  虚拟时间 {dev['virtual_time_s']} s")
            print(f"  PC13 电平 {'高' if pc13['output'] else '低'} → 板载 LED {'亮' if pc13.get('board_led_on') else '灭'}（低电平点亮）")
            print(f"  最近串口：{s['serial_tail'][-4:]}")
            first = await call(session, "serial_read", {"limit": 3})
            await anyio.sleep(4)
            new = await call(session, "serial_read", {"since_seq": first["last_seq"]})
            print(f"  4 秒后新增串口行：{len(new['lines'])} 行 → {[l['text'] for l in new['lines']][:6]}")

            step(4, "能编译但时序错了：LED 应该 500ms 翻转，被写成了 250ms")
            main_c = led / "Core" / "Src" / "main.c"
            main_c.write_text(main_c.read_text(encoding="utf-8").replace("HAL_Delay(500)", "HAL_Delay(250)"), encoding="utf-8")
            b = await call(session, "build", {"project": str(led)})
            print(f"  编译 {ok(b['success'])}  错误 {len(b['errors'])}  警告 {b['warnings']}   ← 只看编译，会以为没问题")
            v = await call(session, "verify_behavior", {"project": str(led), "led": [{"pin": "PC13", "on_ms": 500, "off_ms": 500}]})
            for c in v["checks"]:
                print(f"  行为验证 {ok(c['status'] == 'PASS')} {c['name']}  {D}{c['message'][:90]}{X}")

            step(5, "修好（改回 500ms）再验证")
            main_c.write_text(main_c.read_text(encoding="utf-8").replace("HAL_Delay(250)", "HAL_Delay(500)"), encoding="utf-8")
            v = await call(session, "verify_behavior", {"project": str(led), "led": [{"pin": "PC13", "on_ms": 500, "off_ms": 500}]})
            for c in v["checks"]:
                print(f"  行为验证 {ok(c['status'] == 'PASS')} {c['name']}   证据 {Y}{v['kind']}{X}")
            f = await call(session, "flash", {"project": str(led), "observe_seconds": 1.0})
            print(f"  一键烧录到虚拟板 {ok(f['success'])}，串口无输出（LED 工程不打印）：{f['serial']}")

    shutil.rmtree(work, ignore_errors=True)
    print(f"\n{B}{G}演示结束。{X} 插件退出时已自动关闭虚拟板。")
    print(f"{D}说明：这里全部是 SIMULATED 证据（虚拟 Blue Pill）。接上 ST-Link 后同一套工具走真板，证据变为 HARDWARE。{X}")


if __name__ == "__main__":
    if os.name == "nt":
        os.system("")  # enable ANSI colours in Windows consoles
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    anyio.run(demo)
