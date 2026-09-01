from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.db import connect, now
from app.tools.filesystem import read_file, write_file


TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "hal-uart-init-undef",
        "pattern": "undefined reference to HAL_UART_Init",
        "mcu": "STM32F103",
        "framework": "HAL",
        "tag": "Linker",
        "rootCause": "stm32f1xx_hal_uart.c 未加入 Makefile，或 HAL_UART_MODULE_ENABLED 未开启",
        "fix": "在 Makefile 加入 Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_uart.c，并检查 stm32f1xx_hal_conf.h",
        "strategy": ["检查 HAL Conf", "检查 Makefile", "检查 Driver Src"],
        "files": ["Makefile", "Core/Inc/stm32f1xx_hal_conf.h"],
        "knowledge": ["HAL UART", "CubeF1"],
    },
    {
        "id": "hal-tim-pwm-undef",
        "pattern": "undefined reference to HAL_TIM_PWM_Init",
        "mcu": "STM32F103",
        "framework": "HAL",
        "tag": "Linker",
        "rootCause": "stm32f1xx_hal_tim.c 未加入 Build，或 HAL_TIM_MODULE_ENABLED 未开启",
        "fix": "添加 HAL TIM source 并开启 HAL_TIM_MODULE_ENABLED",
        "strategy": ["检查 HAL Conf", "检查 Makefile", "检查 Driver Src"],
        "files": ["Makefile", "Core/Inc/stm32f1xx_hal_conf.h"],
        "knowledge": ["HAL TIM"],
    },
    {
        "id": "gpio-pin-undeclared",
        "pattern": "GPIO_PIN_x undeclared",
        "mcu": "STM32F103",
        "framework": "HAL",
        "tag": "GPIO",
        "rootCause": "引脚宏未定义或包含了错误的 GPIO 头文件",
        "fix": "使用 GPIO_PIN_13 等合法宏，并 include main.h / stm32f1xx_hal.h",
        "strategy": ["检查引脚宏", "检查 include"],
        "files": ["Core/Inc/gpio.h", "Core/Src/gpio.c"],
        "knowledge": ["HAL GPIO"],
    },
    {
        "id": "multiple-definition",
        "pattern": "multiple definition",
        "mcu": "STM32F103",
        "framework": "HAL",
        "tag": "Linker",
        "rootCause": "同一源文件被编译两次，或非 inline 符号放在头文件",
        "fix": "从 Makefile 去掉重复 .c，或把定义移到 .c",
        "strategy": ["检查 Makefile 重复源", "检查头文件定义"],
        "files": ["Makefile"],
        "knowledge": ["GCC LD"],
    },
]


def ensure_schema() -> None:
    with connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS error_memories (
              id TEXT PRIMARY KEY,
              pattern TEXT,
              mcu TEXT,
              family TEXT,
              framework TEXT,
              tag TEXT,
              root_cause TEXT,
              fix TEXT,
              strategy TEXT,
              files TEXT,
              knowledge TEXT,
              occurrences INTEGER DEFAULT 0,
              successful_runs INTEGER DEFAULT 0,
              failed_runs INTEGER DEFAULT 0,
              last_seen TEXT
            )"""
        )
        for t in TEMPLATES:
            con.execute(
                """INSERT OR IGNORE INTO error_memories
                   (id, pattern, mcu, family, framework, tag, root_cause, fix, strategy, files, knowledge,
                    occurrences, successful_runs, failed_runs)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,0,0,0)""",
                (
                    t["id"],
                    t["pattern"],
                    t["mcu"],
                    "STM32F1",
                    t["framework"],
                    t["tag"],
                    t["rootCause"],
                    t["fix"],
                    json.dumps(t.get("strategy") or []),
                    json.dumps(t.get("files") or []),
                    json.dumps(t.get("knowledge") or []),
                ),
            )


def _row(r: Any) -> dict[str, Any]:
    occ = int(r["occurrences"] or 0)
    ok = int(r["successful_runs"] or 0)
    fail = int(r["failed_runs"] or 0)
    rate = None
    if occ > 0:
        rate = ok / occ
    return {
        "id": r["id"],
        "pattern": r["pattern"],
        "mcu": r["mcu"],
        "family": r["family"],
        "framework": r["framework"],
        "tag": r["tag"],
        "rootCause": r["root_cause"],
        "fix": r["fix"],
        "strategy": json.loads(r["strategy"] or "[]"),
        "files": json.loads(r["files"] or "[]"),
        "knowledge": json.loads(r["knowledge"] or "[]"),
        "occurrences": occ,
        "successRate": rate,
        "successfulRuns": ok,
        "failedRuns": fail,
        "lastSeen": r["last_seen"],
    }


def list_errors(q: str = "", tag: str = "") -> list[dict[str, Any]]:
    ensure_schema()
    with connect() as con:
        rows = con.execute("SELECT * FROM error_memories ORDER BY pattern").fetchall()
    items = [_row(r) for r in rows]
    if tag:
        items = [i for i in items if i["tag"].lower() == tag.lower()]
    if q:
        ql = q.lower()
        items = [
            i
            for i in items
            if ql in i["pattern"].lower() or ql in i["rootCause"].lower() or ql in i["fix"].lower()
        ]
    return items


def get_error(eid: str) -> dict[str, Any] | None:
    ensure_schema()
    with connect() as con:
        r = con.execute("SELECT * FROM error_memories WHERE id=?", (eid,)).fetchone()
    return _row(r) if r else None


def record_from_output(output: str, *, success: bool) -> list[str]:
    ensure_schema()
    hits: list[str] = []
    text = output or ""
    with connect() as con:
        for t in TEMPLATES:
            pat = t["pattern"]
            if pat.lower() in text.lower() or re.search(re.escape(pat.split(" to ")[-1]), text, re.I):
                hits.append(t["id"])
                if success:
                    con.execute(
                        """UPDATE error_memories SET occurrences=occurrences+1, successful_runs=successful_runs+1, last_seen=?
                           WHERE id=?""",
                        (now(), t["id"]),
                    )
                else:
                    con.execute(
                        """UPDATE error_memories SET occurrences=occurrences+1, failed_runs=failed_runs+1, last_seen=?
                           WHERE id=?""",
                        (now(), t["id"]),
                    )
    return hits


def mark_fix_result(eid: str, *, success: bool) -> None:
    ensure_schema()
    with connect() as con:
        if success:
            con.execute(
                """UPDATE error_memories SET occurrences=occurrences+1, successful_runs=successful_runs+1, last_seen=?
                   WHERE id=?""",
                (now(), eid),
            )
        else:
            con.execute(
                """UPDATE error_memories SET occurrences=occurrences+1, failed_runs=failed_runs+1, last_seen=?
                   WHERE id=?""",
                (now(), eid),
            )


_HAL_SRC = {
    "hal-uart-init-undef": (
        "Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_uart.c",
        "HAL_UART_MODULE_ENABLED",
    ),
    "hal-tim-pwm-undef": (
        "Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_tim.c",
        "HAL_TIM_MODULE_ENABLED",
    ),
}


def apply_known_fix(root: Path, error_id: str) -> dict[str, Any]:
    """Mechanically apply a known Makefile / HAL-conf fix. Makefile writes use advanced=True."""
    spec = _HAL_SRC.get(error_id)
    if not spec:
        return {"applied": False, "reason": f"no mechanical fix for {error_id}", "files": []}
    src_rel, macro = spec
    changed: list[str] = []
    notes: list[str] = []

    try:
        mk = read_file(root, "Makefile")
    except FileNotFoundError:
        return {"applied": False, "reason": "Makefile not found", "files": []}
    if src_rel not in mk:
        mk2 = _insert_c_source(mk, src_rel)
        if mk2 != mk:
            write_file(root, "Makefile", mk2, advanced=True)
            changed.append("Makefile")
            notes.append(f"added {src_rel}")
        else:
            notes.append("could not insert C_SOURCES line")
    else:
        notes.append("Makefile already lists source")

    conf_rel = "Core/Inc/stm32f1xx_hal_conf.h"
    try:
        conf = read_file(root, conf_rel)
    except FileNotFoundError:
        conf = None
        notes.append("hal_conf.h not found")
    if conf is not None:
        conf2 = _enable_hal_module(conf, macro)
        if conf2 != conf:
            write_file(root, conf_rel, conf2, advanced=True)
            changed.append(conf_rel)
            notes.append(f"enabled {macro}")
        else:
            notes.append(f"{macro} already enabled or not found")

    return {
        "applied": bool(changed),
        "errorId": error_id,
        "files": changed,
        "notes": notes,
        "reason": None if changed else "; ".join(notes) or "already applied",
    }


def _insert_c_source(makefile: str, rel: str) -> str:
    lines = makefile.splitlines(keepends=True)
    last_src = -1
    for i, line in enumerate(lines):
        if "Drivers/STM32F1xx_HAL_Driver/Src/" in line or line.strip().endswith(".c \\"):
            last_src = i
    if last_src < 0:
        return makefile
    insert = f"\t{rel} \\\n"
    # If previous line ends without backslash, add one
    prev = lines[last_src]
    if not prev.rstrip("\n").endswith("\\"):
        lines[last_src] = prev.rstrip("\n") + " \\\n"
        lines.insert(last_src + 1, insert.rstrip(" \\\n") + "\n")
    else:
        lines.insert(last_src + 1, insert)
    return "".join(lines)


def _enable_hal_module(conf: str, macro: str) -> str:
    define = f"#define {macro}"
    if re.search(rf"^\s*{re.escape(define)}\s*$", conf, re.M):
        return conf
    commented = [
        (rf"/\*\s*{re.escape(define)}\s*\*/", define),
        (rf"//\s*{re.escape(define)}", define),
        (rf"#\s*if\s+0\s*\n\s*{re.escape(define)}\s*\n#endif", define),
    ]
    for pat, repl in commented:
        if re.search(pat, conf):
            return re.sub(pat, repl, conf, count=1)
    # insert after last HAL_*_MODULE_ENABLED define
    m = None
    for m in re.finditer(r"^#define HAL_[A-Z0-9_]+_MODULE_ENABLED\s*$", conf, re.M):
        pass
    if m:
        idx = m.end()
        return conf[:idx] + "\n" + define + conf[idx:]
    return conf + f"\n{define}\n"
