from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from app.core.types import FAIL, PASS, READ_ONLY, SUCCESS, UNKNOWN, WARNING, envelope
from app.mcu.stm32f103 import MCU, PINS, load_board
from app.tools.detect import gcc_installed, make_installed
from app.tools.ioc import parse_ioc as _parse_ioc_text
from app.tools.periph_gen import pin_occupancy
from app.tools.project_scan import scan_existing_project
from app.tools.toolchain import prepend_toolchain_path


RESERVED_BOARD_PINS = {
    "PA13": "SWDIO",
    "PA14": "SWCLK",
    "PC14": "OSC32_IN",
    "PC15": "OSC32_OUT",
    "PD0": "OSC_IN",
    "PD1": "OSC_OUT",
}


def inspect_project_at(root: Path) -> dict[str, Any]:
    scan = scan_existing_project(root)
    prepend_toolchain_path()
    gcc = gcc_installed()
    make = make_installed()
    openocd = shutil.which("openocd") is not None
    analysis = scan.get("analysis") if isinstance(scan.get("analysis"), dict) else None
    mcu_from_ioc = bool(analysis and analysis.get("mcu"))
    mcu = scan.get("mcu")
    board = None
    if analysis:
        board = analysis.get("board")
    pj = _project_json(root)
    if not board:
        board = pj.get("board")
    platform = "STM32"
    family = (analysis or {}).get("family") or _family_from_mcu(str(mcu or ""))
    if not scan.get("ok"):
        return envelope(
            status=FAIL,
            side_effect=READ_ONLY,
            ok=False,
            reason=scan.get("reason") or "inspect failed",
            project_root=str(root),
            warnings=scan.get("warnings") or [],
        )
    toolchain = {
        "arm_gcc": "available" if gcc else "UNAVAILABLE",
        "make": "available" if make else "UNAVAILABLE",
        "openocd": "available" if openocd else "UNAVAILABLE",
        "build_system": scan.get("buildSystem") or "unknown",
    }
    return envelope(
        status=SUCCESS,
        side_effect=READ_ONLY,
        ok=True,
        project_root=str(root),
        platform=platform,
        family=family,
        mcu=mcu,
        mcu_source="ioc" if mcu_from_ioc else "default",
        mcu_defaulted=not mcu_from_ioc,
        board=board or "Blue Pill",
        board_source=_board_source(analysis, pj),
        ioc=scan.get("ioc"),
        cubemx=bool(scan.get("cubemx")),
        framework=scan.get("framework"),
        build_system=scan.get("buildSystem"),
        toolchain=toolchain,
        startup=scan.get("startup") or [],
        linker=scan.get("linker") or [],
        core_files=scan.get("coreFiles") or [],
        drivers=scan.get("drivers") or [],
        middlewares=scan.get("middlewares") or [],
        warnings=scan.get("warnings") or [],
        # keep original scan keys for Web compatibility callers that still want them
        scan=scan,
    )


def parse_ioc_at(root: Path, ioc_path: str | None = None) -> dict[str, Any]:
    path = _resolve_ioc(root, ioc_path)
    if path is None:
        return envelope(
            status=UNKNOWN,
            side_effect=READ_ONLY,
            available=False,
            reason="no .ioc file",
            mcu=None,
            pins=[],
            peripherals={},
            clocks=None,
            usart=[],
            adc=[],
            tim=[],
            spi=[],
            i2c=[],
            dma=[],
            interrupts=[],
        )
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return envelope(status=FAIL, side_effect=READ_ONLY, available=False, reason=str(e))
    analysis = _parse_ioc_text(text, path.name)
    return envelope(
        status=SUCCESS,
        side_effect=READ_ONLY,
        available=True,
        filename=path.name,
        path=str(path.relative_to(root)) if _is_relative_to(path, root) else path.name,
        mcu=analysis.get("mcu"),
        family=analysis.get("family"),
        package=analysis.get("package"),
        board=analysis.get("board"),
        pins=analysis.get("pins") or [],
        gpio=analysis.get("gpio") or [],
        peripherals={
            "usart": analysis.get("usart") or [],
            "spi": analysis.get("spi") or [],
            "i2c": analysis.get("i2c") or [],
            "adc": analysis.get("adc") or [],
            "tim": analysis.get("tim") or [],
            "pwm": analysis.get("pwm") or [],
            "dma": analysis.get("dma") or [],
        },
        clocks=analysis.get("clock"),
        usart=analysis.get("usart") or [],
        adc=analysis.get("adc") or [],
        tim=analysis.get("tim") or [],
        spi=analysis.get("spi") or [],
        i2c=analysis.get("i2c") or [],
        dma=analysis.get("dma") or [],
        interrupts=analysis.get("nvic") or [],
        pwm=analysis.get("pwm") or [],
        nvic=analysis.get("nvic") or [],
        conflicts=analysis.get("conflicts") or [],
        freertos=analysis.get("freertos"),
        middleware=analysis.get("middleware") or [],
        analysis=analysis,
    )


def check_pin_conflicts_at(root: Path) -> dict[str, Any]:
    ioc = parse_ioc_at(root)
    evidence: list[dict[str, Any]] = []
    analysis = ioc.get("analysis") if ioc.get("available") else None
    ioc_conflicts = list((analysis or {}).get("conflicts") or [])
    for item in ioc_conflicts:
        evidence.append({"kind": "ioc", "severity": "FAIL", **item})

    occupancy = pin_occupancy(root)
    for pin, owners in occupancy.items():
        uniq = [o for o in owners if o]
        if len(set(uniq)) > 1:
            evidence.append(
                {
                    "kind": "occupancy",
                    "severity": "FAIL",
                    "pin": pin,
                    "signals": uniq,
                    "detail": f"{pin} claimed by {', '.join(uniq)}",
                }
            )
        reserved = RESERVED_BOARD_PINS.get(str(pin).upper())
        if reserved and any("GPIO" in str(o).upper() or "USART" in str(o).upper() for o in uniq):
            evidence.append(
                {
                    "kind": "reserved",
                    "severity": "WARNING",
                    "pin": pin,
                    "signals": uniq,
                    "detail": f"{pin} is board-reserved ({reserved})",
                }
            )

    pins = (analysis or {}).get("pins") or []
    seen: dict[str, list[str]] = {}
    for p in pins:
        pin = str(p.get("pin") or "")
        sig = str(p.get("signal") or "")
        if pin:
            seen.setdefault(pin, [])
            if sig and sig not in seen[pin]:
                seen[pin].append(sig)
    for pin, sigs in seen.items():
        if len(sigs) > 1:
            evidence.append(
                {
                    "kind": "duplicate",
                    "severity": "FAIL",
                    "pin": pin,
                    "signals": sigs,
                    "detail": f"{pin} duplicated assignment: {' / '.join(sigs)}",
                }
            )

    if not analysis and not occupancy:
        return envelope(
            status=UNKNOWN,
            side_effect=READ_ONLY,
            result="UNKNOWN",
            reason="no IOC and no Core occupancy evidence",
            evidence=[],
        )

    fails = [e for e in evidence if e.get("severity") == "FAIL"]
    warns = [e for e in evidence if e.get("severity") == "WARNING"]
    if fails:
        status = FAIL
        result = "FAIL"
    elif warns:
        status = WARNING
        result = "WARNING"
    else:
        status = PASS
        result = "PASS"
    return envelope(
        status=status,
        side_effect=READ_ONLY,
        result=result,
        evidence=evidence,
        occupancy=occupancy,
        ioc_conflicts=ioc_conflicts,
    )


def get_board_context_at(root: Path) -> dict[str, Any]:
    from app.config.settings import settings

    ioc = parse_ioc_at(root)
    analysis = ioc.get("analysis") if ioc.get("available") else None
    pj = _project_json(root)
    board_profile = load_board(settings.repo_root)

    mcu, mcu_source = _first_defined(
        ((analysis or {}).get("mcu"), "ioc"),
        (pj.get("mcu"), "project"),
        (board_profile.get("mcu"), "board_profile"),
        (MCU["name"], "default"),
    )
    board, board_source = _first_defined(
        ((analysis or {}).get("board"), "ioc"),
        (pj.get("board"), "project"),
        (board_profile.get("board"), "board_profile"),
        ("Blue Pill", "default"),
    )
    led, led_source = _first_defined(
        (_led_from_ioc(analysis), "ioc"),
        (pj.get("led"), "project"),
        (board_profile.get("led"), "board_profile"),
        ("PC13", "default"),
    )

    pin_defs = [{"pin": pin, "functions": fns} for pin, fns in PINS.items()]
    mapping = {
        "led": led,
        "uart": board_profile.get("uart") or "USART1",
        "uart_tx": board_profile.get("uart_tx") or "PA9",
        "uart_rx": board_profile.get("uart_rx") or "PA10",
        "debug": board_profile.get("debug") or "SWD",
        "oscillator": board_profile.get("oscillator") or "8MHz HSE",
    }
    limitations = [
        "Production support is STM32F103 only.",
        "PA13/PA14 are SWD; do not reuse without disabling debug.",
        "Blue Pill LED is PC13 active-low.",
        "Compile success is not hardware PASS.",
    ]
    return envelope(
        status=SUCCESS,
        side_effect=READ_ONLY,
        mcu=mcu,
        board=board,
        led=led,
        flash_kb=MCU.get("flash_kb"),
        ram_kb=MCU.get("ram_kb"),
        family=MCU.get("family"),
        pin_definitions=pin_defs,
        peripheral_mapping=mapping,
        known_limitations=limitations,
        sources={
            "mcu": mcu_source,
            "board": board_source,
            "led": led_source,
            "priority": "IOC > project.json > Board Profile > Default",
        },
        ioc_available=bool(analysis),
        project_config=pj or None,
        board_profile=board_profile,
    )


def _project_json(root: Path) -> dict[str, Any]:
    pj = root / "project.json"
    if not pj.is_file():
        return {}
    try:
        data = json.loads(pj.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _board_source(analysis: dict[str, Any] | None, pj: dict[str, Any]) -> str:
    if analysis and analysis.get("board"):
        return "ioc"
    if pj.get("board"):
        return "project"
    return "default"


def _family_from_mcu(mcu: str) -> str | None:
    up = (mcu or "").upper()
    if "STM32F1" in up:
        return "STM32F1"
    if up.startswith("STM32"):
        return up[:7]
    return None


def _resolve_ioc(root: Path, ioc_path: str | None) -> Path | None:
    if ioc_path:
        from app.core.security import PathEscapeError, resolve_under

        try:
            candidate = resolve_under(root, ioc_path)
        except PathEscapeError:
            candidate = (root / ioc_path).resolve() if not Path(ioc_path).is_absolute() else Path(ioc_path).resolve()
            if candidate != root and root not in candidate.parents:
                return None
        return candidate if candidate.is_file() else None
    cached = list(root.glob("*.ioc")) + list(root.glob("**/*.ioc"))
    files = [p for p in cached if p.is_file()]
    return files[0] if files else None


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _first_defined(*pairs: tuple[Any, str]) -> tuple[Any, str]:
    for value, source in pairs:
        if value not in (None, "", []):
            return value, source
    last = pairs[-1]
    return last[0], last[1]


def _led_from_ioc(ioc: dict[str, Any] | None) -> str | None:
    if not ioc:
        return None
    for p in ioc.get("pins") or []:
        sig = str(p.get("signal") or "")
        pin = str(p.get("pin") or "")
        if pin.upper() == "PC13" or "LED" in sig.upper():
            return pin or "PC13"
    return None
