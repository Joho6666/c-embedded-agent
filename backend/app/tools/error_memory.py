from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.db import connect, now
from app.tools.filesystem import read_file, write_file
from app.tools.hal_modules import register_hal_module


def _t(
    eid: str,
    pattern: str,
    *,
    tag: str,
    root: str,
    fix: str,
    files: list[str],
    knowledge: list[str],
    mechanical: str | None = None,
    regex: str | None = None,
) -> dict[str, Any]:
    return {
        "id": eid,
        "pattern": pattern,
        "regex": regex,
        "mcu": "STM32F103",
        "framework": "HAL",
        "tag": tag,
        "rootCause": root,
        "fix": fix,
        "strategy": ["Error Signature", "Known Fix", "Apply", "Build"],
        "files": files,
        "knowledge": knowledge,
        "mechanical": mechanical,
    }


TEMPLATES: list[dict[str, Any]] = [
    _t(
        "hal-uart-init-undef",
        "undefined reference to HAL_UART_Init",
        tag="Linker",
        root="stm32f1xx_hal_uart.c 未加入 Makefile，或 HAL_UART_MODULE_ENABLED 未开启",
        fix="register_hal_module UART",
        files=["Makefile", "Core/Inc/stm32f1xx_hal_conf.h"],
        knowledge=["HAL UART"],
        mechanical="UART",
    ),
    _t(
        "hal-tim-pwm-undef",
        "undefined reference to HAL_TIM_PWM_Init",
        tag="Linker",
        root="stm32f1xx_hal_tim.c 未加入 Build，或 HAL_TIM_MODULE_ENABLED 未开启",
        fix="register_hal_module TIM",
        files=["Makefile", "Core/Inc/stm32f1xx_hal_conf.h"],
        knowledge=["HAL TIM"],
        mechanical="TIM",
    ),
    _t(
        "hal-adc-init-undef",
        "undefined reference to HAL_ADC_Init",
        tag="Linker",
        root="stm32f1xx_hal_adc.c 未加入 Makefile",
        fix="register_hal_module ADC",
        files=["Makefile", "Core/Inc/stm32f1xx_hal_conf.h"],
        knowledge=["HAL ADC"],
        mechanical="ADC",
    ),
    _t(
        "hal-adc-start-dma-undef",
        "undefined reference to HAL_ADC_Start_DMA",
        tag="Linker",
        root="ADC DMA API 需要 HAL ADC + DMA source",
        fix="register_hal_module ADC and DMA",
        files=["Makefile", "Core/Inc/stm32f1xx_hal_conf.h"],
        knowledge=["HAL ADC DMA"],
        mechanical="ADC,DMA",
    ),
    _t(
        "hal-i2c-init-undef",
        "undefined reference to HAL_I2C_Init",
        tag="Linker",
        root="stm32f1xx_hal_i2c.c 未加入 Makefile",
        fix="register_hal_module I2C",
        files=["Makefile", "Core/Inc/stm32f1xx_hal_conf.h"],
        knowledge=["HAL I2C"],
        mechanical="I2C",
    ),
    _t(
        "hal-spi-init-undef",
        "undefined reference to HAL_SPI_Init",
        tag="Linker",
        root="stm32f1xx_hal_spi.c 未加入 Makefile",
        fix="register_hal_module SPI",
        files=["Makefile", "Core/Inc/stm32f1xx_hal_conf.h"],
        knowledge=["HAL SPI"],
        mechanical="SPI",
    ),
    _t(
        "hal-uart-receive-dma-undef",
        "undefined reference to HAL_UART_Receive_DMA",
        tag="Linker",
        root="UART DMA API 需要 HAL UART + DMA source",
        fix="register_hal_module UART and DMA",
        files=["Makefile", "Core/Inc/stm32f1xx_hal_conf.h"],
        knowledge=["HAL UART DMA"],
        mechanical="UART,DMA",
    ),
    _t(
        "dma-handler-missing",
        "undefined reference to DMA1_Channel5_IRQHandler",
        tag="Linker",
        root="DMA IRQ handler 未实现",
        fix="在 stm32f1xx_it.c 添加 DMA1_Channel5_IRQHandler 并调用 HAL_DMA_IRQHandler",
        files=["Core/Src/stm32f1xx_it.c", "Core/Inc/stm32f1xx_it.h"],
        knowledge=["HAL DMA"],
        mechanical="irq:DMA1_Channel5",
        regex=r"undefined reference to [`']?DMA1_Channel\d+_IRQHandler",
    ),
    _t(
        "irq-handler-missing",
        "undefined reference to USART1_IRQHandler",
        tag="Linker",
        root="IRQ handler 未实现",
        fix="在 stm32f1xx_it.c 添加对应 IRQHandler",
        files=["Core/Src/stm32f1xx_it.c"],
        knowledge=["NVIC"],
        mechanical="irq:auto",
        regex=r"undefined reference to [`']?([A-Z0-9_]+_IRQHandler)",
    ),
    _t(
        "hal-module-disabled",
        "HAL module disabled",
        tag="HAL",
        root="stm32f1xx_hal_conf.h 中对应 HAL_*_MODULE_ENABLED 被注释",
        fix="取消注释对应 MODULE_ENABLED",
        files=["Core/Inc/stm32f1xx_hal_conf.h"],
        knowledge=["HAL Conf"],
        regex=r"#error.+HAL_.*_MODULE_ENABLED|is disabled",
    ),
    _t(
        "duplicate-source",
        "multiple definition",
        tag="Linker",
        root="同一源文件被编译两次",
        fix="从 Makefile 去掉重复 .c",
        files=["Makefile"],
        knowledge=["GCC LD"],
        mechanical="dedupe",
    ),
    _t(
        "f4-api-on-f1",
        "GPIO_AF",
        tag="API",
        root="在 F1 上使用了 STM32F4 GPIO alternate function API",
        fix="F1 使用 GPIO_MODE_AF_PP，不要调用 HAL_GPIO_Init Alternate 的 GPIO_AF7 风格 API",
        files=["Core/Src"],
        knowledge=["HAL GPIO F1"],
        regex=r"GPIO_AF\d+|HAL_GPIO_Init.+Alternate",
    ),
    _t(
        "gpio-af-mismatch",
        "GPIO alternate function API mismatch",
        tag="GPIO",
        root="STM32F1 没有 HAL_GPIO_Init 的 Alternate 字段 / GPIO_AF_*",
        fix="F1 USART/TIM AF 使用 GPIO_MODE_AF_PP，无需 GPIO_AF7_USART1",
        files=["Core/Src"],
        knowledge=["HAL GPIO F1"],
        regex=r"GPIO_AF7_USART|GPIO_AF1_TIM|Alternate\s*=",
    ),
    _t(
        "missing-peripheral-source",
        "missing peripheral source",
        tag="Linker",
        root="外设 .c 未加入 Makefile",
        fix="register_hal_module for the undefined HAL_* symbol",
        files=["Makefile"],
        knowledge=["Makefile"],
        regex=r"undefined reference to [`']?HAL_([A-Z]+)_",
    ),
    _t(
        "missing-irq-source",
        "undefined reference to HAL_TIM_IRQHandler",
        tag="Linker",
        root="IRQ 调用了 HAL_*_IRQHandler 但 TIM/UART/DMA 模块未链接",
        fix="register corresponding HAL module",
        files=["Makefile"],
        knowledge=["NVIC"],
        mechanical="TIM",
    ),
    _t(
        "gpio-pin-undeclared",
        "GPIO_PIN_x undeclared",
        tag="GPIO",
        root="引脚宏未定义",
        fix="使用 GPIO_PIN_0..15 并 include stm32f1xx_hal.h",
        files=["Core/Inc/gpio.h"],
        knowledge=["HAL GPIO"],
        regex=r"GPIO_PIN_\d+\s+undeclared",
    ),
    _t(
        "multiple-definition",
        "multiple definition",
        tag="Linker",
        root="同一源文件被编译两次，或非 inline 符号放在头文件",
        fix="从 Makefile 去掉重复 .c",
        files=["Makefile"],
        knowledge=["GCC LD"],
        mechanical="dedupe",
    ),
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


def match_known_errors(output: str) -> list[dict[str, Any]]:
    text = output or ""
    hits: list[dict[str, Any]] = []
    seen: set[str] = set()
    for t in TEMPLATES:
        pat = t["pattern"]
        rx = t.get("regex")
        ok = pat.lower() in text.lower()
        if not ok and rx:
            ok = bool(re.search(rx, text, re.I))
        if not ok:
            token = pat.split(" to ")[-1]
            if token and token != pat:
                ok = bool(re.search(re.escape(token), text, re.I))
        if ok and t["id"] not in seen:
            seen.add(t["id"])
            hits.append({**t, "mechanical": bool(t.get("mechanical"))})
    return hits


def record_from_output(output: str, *, success: bool) -> list[str]:
    ensure_schema()
    hits = [h["id"] for h in match_known_errors(output)]
    with connect() as con:
        for eid in hits:
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


def apply_known_fix(root: Path, error_id: str) -> dict[str, Any]:
    """Mechanically apply a known fix. Makefile writes use advanced=True."""
    spec = next((t for t in TEMPLATES if t["id"] == error_id), None)
    if not spec or not spec.get("mechanical"):
        return {"applied": False, "reason": f"no mechanical fix for {error_id}", "files": []}
    mech = str(spec["mechanical"])
    changed: list[str] = []
    notes: list[str] = []
    if mech == "dedupe":
        try:
            mk = read_file(root, "Makefile")
        except FileNotFoundError:
            return {"applied": False, "reason": "Makefile not found", "files": []}
        mk2 = _dedupe_makefile_sources(mk)
        if mk2 != mk:
            write_file(root, "Makefile", mk2, advanced=True)
            return {"applied": True, "errorId": error_id, "files": ["Makefile"], "notes": ["removed duplicate C_SOURCES"]}
        return {"applied": False, "reason": "no duplicate sources", "files": []}
    if mech.startswith("irq:"):
        irq = mech.split(":", 1)[1]
        out = _ensure_irq_handler(root, irq)
        return {"applied": bool(out.get("applied")), "errorId": error_id, **out}
    for mod in mech.split(","):
        mod = mod.strip()
        if not mod:
            continue
        res = register_hal_module(root, mod)
        notes.extend(res.get("notes") or [])
        changed.extend(res.get("files") or [])
    uniq = list(dict.fromkeys(changed))
    return {
        "applied": bool(uniq),
        "errorId": error_id,
        "files": uniq,
        "notes": notes,
        "reason": None if uniq else "; ".join(notes) or "already applied",
    }


def _dedupe_makefile_sources(makefile: str) -> str:
    seen: set[str] = set()
    out: list[str] = []
    for line in makefile.splitlines(keepends=True):
        m = re.search(r"(Drivers/STM32F1xx_HAL_Driver/Src/\S+\.c|Core/Src/\S+\.c)", line)
        if m:
            src = m.group(1)
            if src in seen:
                continue
            seen.add(src)
        out.append(line)
    return "".join(out)


def _ensure_irq_handler(root: Path, irq: str) -> dict[str, Any]:
    rel = "Core/Src/stm32f1xx_it.c"
    try:
        text = read_file(root, rel)
    except FileNotFoundError:
        return {"applied": False, "reason": "stm32f1xx_it.c missing", "files": []}
    name = "DMA1_Channel5_IRQHandler" if irq in {"DMA1_Channel5", "auto"} else irq
    if name in text:
        return {"applied": False, "reason": f"{name} already present", "files": []}
    stub = (
        f"\nvoid {name}(void)\n"
        "{\n"
        "  /* known-fix stub: call matching HAL IRQ if handle exists in this translation unit */\n"
        "}\n"
    )
    write_file(root, rel, text.rstrip() + stub + "\n")
    hdr = "Core/Inc/stm32f1xx_it.h"
    try:
        h = read_file(root, hdr)
        if name not in h:
            write_file(root, hdr, h.replace("#ifdef __cplusplus", f"void {name}(void);\n#ifdef __cplusplus", 1) if "#ifdef __cplusplus" in h else h + f"\nvoid {name}(void);\n")
    except FileNotFoundError:
        pass
    return {"applied": True, "files": [rel], "notes": [f"added {name}"]}
