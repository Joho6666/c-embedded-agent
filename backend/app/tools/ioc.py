from __future__ import annotations

import re
from typing import Any


def parse_ioc(content: str, filename: str = "project.ioc") -> dict[str, Any]:
    kv: dict[str, str] = {}
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        kv[key.strip()] = value.strip()

    mcu = kv.get("Mcu.Name") or kv.get("Mcu.UserName") or kv.get("Mcu.CPN")
    family = kv.get("Mcu.Family") or _family_from_mcu(mcu)
    package = kv.get("Mcu.Package") or kv.get("Mcu.UserName")

    clock = _clock_tree(kv)
    pins = _pins(kv)
    conflicts = _conflicts(pins)
    periph = _peripherals(kv, pins)
    nvic = sorted({v for k, v in kv.items() if k.startswith("NVIC.") and v and v not in {"true", "false", "ENABLE", "DISABLE"}})
    freertos = any("FREERTOS" in k.upper() or "FreeRTOS" in k for k in kv)
    middleware = _middleware(kv)
    board = _guess_board(mcu, clock, pins)

    return {
        "filename": filename,
        "mcu": mcu,
        "family": family,
        "package": package,
        "board": board,
        "clock": clock,
        "pins": pins,
        "gpio": [p for p in pins if (p.get("peripheral") or "").upper().startswith("GPIO") or "GPIO" in (p.get("signal") or "")],
        "usart": periph["usart"],
        "spi": periph["spi"],
        "i2c": periph["i2c"],
        "adc": periph["adc"],
        "tim": periph["tim"],
        "pwm": periph["pwm"],
        "dma": periph["dma"],
        "nvic": nvic[:40],
        "freertos": freertos,
        "middleware": middleware,
        "conflicts": conflicts,
        "rawKeys": len(kv),
    }


def _family_from_mcu(mcu: str | None) -> str | None:
    if not mcu:
        return None
    m = re.match(r"(STM32[A-Z0-9]+)", mcu.upper())
    if not m:
        return None
    name = m.group(1)
    if name.startswith("STM32F1"):
        return "STM32F1"
    if name.startswith("STM32F4"):
        return "STM32F4"
    return name[:7]


def _mhz(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        v = float(raw)
    except ValueError:
        m = re.search(r"([\d.]+)", raw)
        if not m:
            return None
        v = float(m.group(1))
    if v > 1000:
        return int(v)
    return int(v * 1_000_000)


def _clock_tree(kv: dict[str, str]) -> dict[str, Any]:
    hse = _mhz(kv.get("RCC.HSE_VALUE") or kv.get("RCC.HSEFreq_Value") or kv.get("PCC.HSE"))
    hsi = _mhz(kv.get("RCC.HSI_VALUE") or kv.get("RCC.HSIFreq_Value")) or 8_000_000
    pll_mul = None
    for key in ("RCC.PLLMUL", "RCC.PLLMul", "RCC.PLLCLKFreq_Value"):
        if key in kv:
            m = re.search(r"(\d+)", kv[key])
            if m:
                pll_mul = int(m.group(1))
                break
    sysclk = _mhz(kv.get("RCC.SYSCLKFreq_VALUE") or kv.get("RCC.SYSCLKFreq_Value") or kv.get("PCC.Frequency"))
    if not sysclk and hse and pll_mul:
        sysclk = hse * pll_mul
    if not sysclk:
        sysclk = 72_000_000 if (hse or 0) == 8_000_000 else hsi
    ahb = _mhz(kv.get("RCC.AHBFreq_Value") or kv.get("RCC.AHBCLKDivider")) or sysclk
    apb1 = _mhz(kv.get("RCC.APB1Freq_Value")) or (sysclk // 2 if sysclk >= 72_000_000 else sysclk)
    apb2 = _mhz(kv.get("RCC.APB2Freq_Value")) or sysclk
    pll_src = kv.get("RCC.PLLSource") or kv.get("RCC.PLLCLKSource") or ("HSE" if hse else "HSI")
    nodes = []
    if hse:
        nodes.append({"id": "hse", "label": f"HSE {hse // 1_000_000}MHz", "hz": hse})
    nodes.append({"id": "hsi", "label": f"HSI {hsi // 1_000_000}MHz", "hz": hsi})
    if pll_mul:
        nodes.append({"id": "pll", "label": f"PLL ×{pll_mul}", "hz": (hse or hsi) * pll_mul, "note": pll_src})
    nodes.append({"id": "sysclk", "label": f"SYSCLK {sysclk // 1_000_000}MHz", "hz": sysclk})
    nodes.append({"id": "ahb", "label": f"AHB {ahb // 1_000_000}MHz", "hz": ahb})
    nodes.append({"id": "apb1", "label": f"APB1 {apb1 // 1_000_000}MHz", "hz": apb1})
    nodes.append({"id": "apb2", "label": f"APB2 {apb2 // 1_000_000}MHz", "hz": apb2})
    return {
        "hseHz": hse,
        "hsiHz": hsi,
        "pllMul": pll_mul,
        "pllSource": pll_src,
        "sysclkHz": sysclk,
        "ahbHz": ahb,
        "apb1Hz": apb1,
        "apb2Hz": apb2,
        "nodes": nodes,
    }


_PIN_RE = re.compile(r"^(P[A-K]\d{1,2})\.(Signal|Mode|Locked|GPIO_Label|Stm32CubeMx_Label)$")


def _pins(kv: dict[str, str]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, str]] = {}
    for key, value in kv.items():
        m = _PIN_RE.match(key)
        if not m:
            continue
        pin, field = m.group(1), m.group(2)
        grouped.setdefault(pin, {})[field] = value
    # VP / PinOut style
    for key, value in kv.items():
        if key.startswith("PinOut.") and value:
            pin = value.split(":")[0] if ":" in value else None
        else:
            pin = None
        if pin and re.match(r"^P[A-K]\d{1,2}$", pin):
            grouped.setdefault(pin, {})
    pins: list[dict[str, Any]] = []
    for pin, fields in sorted(grouped.items()):
        signal = fields.get("Signal") or fields.get("GPIO_Label") or fields.get("Stm32CubeMx_Label") or "GPIO"
        mode = fields.get("Mode")
        peripheral = signal.split("_")[0] if "_" in signal else ("GPIO" if "GPIO" in signal else signal)
        direction = "af"
        if "GPIO_Output" in signal or mode in {"Output", "GPIO_Output"}:
            direction = "out"
        elif "GPIO_Input" in signal or mode in {"Input", "GPIO_Input"}:
            direction = "in"
        elif "ADC" in signal or mode == "Analog":
            direction = "analog"
        pins.append(
            {
                "pin": pin,
                "signal": signal,
                "mode": mode,
                "peripheral": peripheral,
                "direction": direction,
                "locked": fields.get("Locked") == "true",
            }
        )
    return pins


def _conflicts(pins: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_pin: dict[str, list[str]] = {}
    for p in pins:
        by_pin.setdefault(p["pin"], []).append(p["signal"])
    out = []
    for pin, signals in by_pin.items():
        uniq = sorted(set(s for s in signals if s))
        gpio_and_af = any("GPIO" in s for s in uniq) and any("_" in s and "GPIO" not in s for s in uniq)
        if len(uniq) > 1 and gpio_and_af:
            out.append({"pin": pin, "signals": uniq, "detail": f"{pin} 同时配置为 {' / '.join(uniq)}"})
    return out


def _peripherals(kv: dict[str, str], pins: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    buckets = {"usart": [], "spi": [], "i2c": [], "adc": [], "tim": [], "pwm": [], "dma": []}
    seen: set[tuple[str, str]] = set()

    def add(kind: str, name: str, extra: dict[str, str] | None = None) -> None:
        key = (kind, name)
        if key in seen:
            return
        seen.add(key)
        buckets[kind].append({"name": name, "kind": kind, "enabled": True, "params": extra or {}})

    for p in pins:
        sig = (p.get("signal") or "").upper()
        if sig.startswith("USART") or sig.startswith("UART"):
            add("usart", sig.split("_")[0])
        elif sig.startswith("SPI"):
            add("spi", sig.split("_")[0])
        elif sig.startswith("I2C"):
            add("i2c", sig.split("_")[0])
        elif sig.startswith("ADC"):
            add("adc", sig.split("_")[0])
        elif sig.startswith("TIM"):
            name = sig.split("_")[0]
            add("tim", name)
            if "CH" in sig or "PWM" in sig:
                add("pwm", name, {"channel": sig})
        elif "DMA" in sig:
            add("dma", sig.split("_")[0] if "_" in sig else sig)

    for key, value in kv.items():
        up = key.upper()
        if up.startswith("USART") or up.startswith("UART"):
            add("usart", key.split(".")[0])
        elif up.startswith("SPI"):
            add("spi", key.split(".")[0])
        elif up.startswith("I2C"):
            add("i2c", key.split(".")[0])
        elif up.startswith("ADC"):
            add("adc", key.split(".")[0])
        elif up.startswith("TIM"):
            add("tim", key.split(".")[0])
        elif "DMA" in up and value not in {"", "Disable"}:
            add("dma", key.split(".")[0])
        if "PWM" in up:
            add("pwm", key.split(".")[0])
    return buckets


def _middleware(kv: dict[str, str]) -> list[str]:
    names = []
    for key in kv:
        if key.startswith("VP_") or "Middleware" in key or key.startswith("FREERTOS"):
            part = key.split(".")[0].replace("VP_", "")
            if part and part not in names:
                names.append(part)
    return names[:20]


def _guess_board(mcu: str | None, clock: dict[str, Any], pins: list[dict[str, Any]]) -> str | None:
    pin_set = {p["pin"] for p in pins}
    hse = clock.get("hseHz") or 0
    if mcu and "F103C8" in mcu.upper() and (hse in (0, 8_000_000)) and ("PC13" in pin_set or not pin_set):
        return "Blue Pill"
    return None
