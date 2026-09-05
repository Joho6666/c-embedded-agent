from __future__ import annotations

from pathlib import Path
from typing import Any

from app.validation.adc import validate_adc
from app.validation.base import ValidationResult, core_source_text, result_dict
from app.validation.dma import validate_dma
from app.validation.exti import validate_exti
from app.validation.gpio import validate_gpio
from app.validation.i2c import validate_i2c
from app.validation.pwm import validate_pwm
from app.validation.spi import validate_spi
from app.validation.tim import validate_tim
from app.validation.review import review_project
from app.validation.usart import validate_usart


def select_validators(prompt: str) -> list[str]:
    p = (prompt or "").lower()
    kinds: list[str] = []
    mapping = (
        ("usart-dma", ("usart dma", "uart dma", "dma uart", "receive_dma")),
        ("usart-it", ("usart interrupt", "uart interrupt", "receive_it", "usart_it", "中断接收")),
        ("usart", ("usart", "uart", "串口", "printf")),
        ("adc-dma", ("adc dma",)),
        ("adc", ("adc",)),
        ("pwm", ("pwm", "舵机", "servo")),
        ("tim", ("tim interrupt", "tim3", "tim2", "定时器", "timer")),
        ("exti", ("exti",)),
        ("i2c", ("i2c", "eeprom")),
        ("spi", ("spi",)),
        ("gpio", ("led", "gpio", "blink", "闪")),
        ("dma", ("dma",)),
    )
    for kind, keys in mapping:
        if any(k in p for k in keys) and kind not in kinds:
            kinds.append(kind)
    if not kinds:
        kinds = ["gpio"]
    return kinds


def validate_project(root: Path, prompt: str = "") -> dict[str, Any]:
    kinds = select_validators(prompt)
    checks: dict[str, bool] = {}
    missing: list[str] = []
    per: dict[str, Any] = {}
    for kind in kinds:
        fn = {
            "gpio": validate_gpio,
            "exti": validate_exti,
            "usart": validate_usart,
            "usart-it": lambda r: validate_usart(r, mode="interrupt"),
            "usart-dma": lambda r: validate_usart(r, mode="dma"),
            "dma": validate_dma,
            "tim": validate_tim,
            "pwm": validate_pwm,
            "adc": validate_adc,
            "adc-dma": lambda r: validate_adc(r, mode="dma"),
            "i2c": validate_i2c,
            "spi": validate_spi,
        }.get(kind)
        if not fn:
            continue
        item = fn(root)
        per[kind] = item
        for k, v in (item.get("checks") or {}).items():
            checks[f"{kind}.{k}"] = bool(v)
        missing.extend(f"{kind}.{m}" for m in (item.get("missing") or []))
    review = review_project(root)
    per["review"] = review
    for k, v in (review.get("checks") or {}).items():
        checks[f"review.{k}"] = bool(v)
    missing.extend(f"review.{m}" for m in (review.get("missing") or []))
    n = max(len(checks), 1)
    score = round(sum(1 for v in checks.values() if v) / n, 4)
    review_fail = bool(review.get("missing"))
    passed = (
        score >= 0.8
        and not review_fail
        and not any(str(m).endswith((".hal_init", ".clock", ".module")) for m in missing)
    )
    return result_dict(passed=passed, score=score, checks=checks, missing=missing, extra={"kinds": kinds, "per": per})


def hardware_status(*, serial_lines: list[str] | None, expect: str | None, task: str, has_probe: bool) -> dict[str, Any]:
    """Never fake PASS. Distinguish PASS/FAIL/PARTIAL/UNKNOWN/UNAVAILABLE/MANUAL_STEP_REQUIRED/WAITING_FOR_USER."""
    kind = (task or "").lower()
    joined = "\n".join(serial_lines or [])

    # Human-in-the-loop: 8051 cold power-cycle ISP requirement
    if ("8051" in kind or "stc" in kind) and "isp" in kind:
        return {
            "status": "MANUAL_STEP_REQUIRED",
            "state": "WAITING_FOR_USER",
            "manual_step": "power_cycle",
            "reason": "Please power cycle STC89C52 within 10 seconds to initiate ISP programming",
            "observed": joined[:400],
        }

    # Human-in-the-loop: external button / EXTI actuation
    if kind in {"exti", "button"} or "按键" in kind:
        return {
            "status": "MANUAL_STEP_REQUIRED",
            "state": "WAITING_FOR_USER",
            "manual_step": "button_press",
            "reason": "EXTI requires manual user button press; physical actuation cannot be automated without hardware test bench",
            "observed": joined[:400],
        }

    if kind in {"pwm"} and not has_probe:
        return {"status": "PARTIAL", "reason": "no measurement device (oscilloscope/logic analyzer required)", "observed": joined[:400]}
    if kind in {"led", "gpio"} and not has_probe:
        return {"status": "PARTIAL", "reason": "firmware flashed, but optical sensor/probe required to verify LED blinking; cannot confirm physical light emission", "hardware": "PARTIAL"}
    if serial_lines is None and not has_probe:
        return {"status": "UNAVAILABLE", "reason": "Hardware Not Tested"}
    if not serial_lines:
        return {"status": "UNKNOWN", "reason": "no serial evidence"}

    if kind.startswith("usart") or kind == "uart" or "serial" in kind:
        valid_markers = ("CEA:STM32:PASS", "CEA:ESP32:PASS", "CEA:8051:PASS", "CEA:USART:PASS")
        ok = any(m in joined for m in valid_markers) or (bool(expect) and expect in joined)
        return {"status": "PASS" if ok else "FAIL", "observed": joined[-800:], "verdict": "VERIFIED_HARDWARE" if ok else "FAIL"}

    if kind.startswith("adc"):
        import re

        m = re.search(r"CEA:ADC:value=(\d+)", joined)
        if not m:
            return {"status": "FAIL", "reason": "missing CEA:ADC:value telemetry range marker", "observed": joined[-800:]}
        value = int(m.group(1))
        ok = 0 <= value <= 4095
        return {"status": "PASS" if ok else "FAIL", "value": value, "observed": joined[-800:], "verdict": "VERIFIED_HARDWARE" if ok else "FAIL"}

    needle = (expect or "").strip()
    if needle:
        ok = needle.lower() in joined.lower()
        return {"status": "PASS" if ok else "FAIL", "observed": joined[-800:], "verdict": "VERIFIED_HARDWARE" if ok else "FAIL"}
    return {"status": "UNKNOWN", "reason": "no hardware rule", "observed": joined[-400:]}


__all__ = [
    "ValidationResult",
    "core_source_text",
    "hardware_status",
    "select_validators",
    "validate_project",
]
