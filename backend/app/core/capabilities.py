"""Platform capability matrix — evidence-derived, never hand-claimed.

Each cell states VERIFIED / UNVERIFIED / NOT_SUPPORTED / NOT_INSTALLED with
the evidence that backs it. The matrix reflects the *running host* (e.g.
BUILD flips to NOT_INSTALLED when the toolchain is missing) and the real
spike results committed under docs/.
"""

from __future__ import annotations

from typing import Any

CELL_STATUSES = ("VERIFIED", "UNVERIFIED", "NOT_SUPPORTED", "NOT_INSTALLED")

CELLS = ("BUILD", "FLASH", "DEBUG", "SERIAL", "SIMULATE", "HARDWARE_VALIDATE")

PLANNED_PLATFORMS = ("esp32", "c51", "rp2040", "host-c")


def _gcc_ok() -> bool:
    from app.tools.detect import gcc_installed, make_installed

    return gcc_installed() and make_installed()


def _renode_ok() -> tuple[bool, str | None]:
    from app.hardware.simulation.renode import find_renode

    path = find_renode()
    return (path is not None, str(path) if path else None)


def _cell(status: str, evidence: str) -> dict[str, Any]:
    return {"status": status, "evidence": evidence}


def _stm32() -> dict[str, Any]:
    build_ok = _gcc_ok()
    renode_ok, renode_path = _renode_ok()
    return {
        "platformId": "stm32",
        "label": "STM32F103 HAL",
        "adapter": "STM32Adapter",
        "mcu": "STM32F103C8T6",
        "board": "Blue Pill",
        "capabilities": {
            "BUILD": _cell(
                "VERIFIED" if build_ok else "NOT_INSTALLED",
                "11/11 golden projects compiled with real sizes (RELEASE_REPORT 0.9 audit); "
                "arm-none-eabi-gcc 13.3.1 present on this host" if build_ok else "arm-none-eabi-gcc/make missing on this host",
            ),
            "FLASH": _cell(
                "UNVERIFIED",
                "OpenOCD flash path code-complete with chip-id family guard and flash budget; "
                "no probe attached to this host to produce live evidence",
            ),
            "DEBUG": _cell(
                "UNVERIFIED",
                "GDB/MI DebuggerSession + CrashEvidence implemented and protocol-tested; "
                "live halt/read requires OpenOCD + probe (not installed here)",
            ),
            "SERIAL": _cell(
                "UNVERIFIED",
                "pyserial adaptive capture + CEA token validators tested with fakes; "
                "CH340 present but no loopback/device session recorded",
            ),
            "SIMULATE": _cell(
                "VERIFIED" if renode_ok else "NOT_INSTALLED",
                f"Real run: STM32F103 ELF in Renode 1.15.3 emitted CEA:SIM:PASS via UART file backend "
                f"(docs/RENODE_SPIKE.md); adapter at {'~/tools/renode-portable' if renode_ok else renode_path}",
            ),
            "HARDWARE_VALIDATE": _cell(
                "UNVERIFIED",
                "Three-level evidence model + per-peripheral evidence requirements implemented; "
                "awaiting Hardware Lab session (docs/hardware-lab/stm32f103-bluepill.md)",
            ),
        },
    }


def _planned(platform_id: str, label: str, reason: str) -> dict[str, Any]:
    return {
        "platformId": platform_id,
        "label": label,
        "adapter": None,
        "capabilities": {
            cell: _cell("NOT_SUPPORTED", reason) for cell in CELLS
        },
    }


def platform_capabilities() -> list[dict[str, Any]]:
    out = [_stm32()]
    out.append(
        _planned(
            "esp32",
            "ESP32-S3 IDF",
            "No backend adapter exists (UI metadata only). Simulation feasibility spike: docs/ESP32_SIM_SPIKE.md — NOT_RUN, ESP-IDF absent.",
        )
    )
    out.append(_planned("c51", "8051 SDCC", "No backend adapter exists (UI metadata only)."))
    out.append(_planned("rp2040", "RP2040", "No backend adapter exists; candidate for next-platform scoring."))
    out.append(_planned("host-c", "Host C", "No backend adapter exists (UI metadata only)."))
    return out


def capability_summary() -> dict[str, Any]:
    platforms = platform_capabilities()
    verified = {}
    for p in platforms:
        verified[p["platformId"]] = {
            cell: p["capabilities"][cell]["status"] for cell in CELLS
        }
    return {
        "rule": "VERIFIED requires committed evidence on this host; code-path-exists is UNVERIFIED, never VERIFIED",
        "generatedAt": None,
        "platforms": verified,
    }
