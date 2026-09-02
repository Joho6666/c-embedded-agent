from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.tools.toolchain import prepend_toolchain_path


def _run_version(exe_name: str, extra_args: list[str] | None = None) -> str | None:
    prepend_toolchain_path()
    if shutil.which(exe_name) is None:
        return None
    args = [exe_name]
    args.extend(extra_args or ["--version"])
    try:
        r = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
            shell=False,
        )
        line = (r.stdout or r.stderr).splitlines()
        return line[0].strip() if line else exe_name
    except (OSError, subprocess.TimeoutExpired):
        return None


def _which_any(names: list[str]) -> str | None:
    prepend_toolchain_path()
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def _install_status(installed: bool, version: str | None = None, configured: bool | None = None) -> str:
    if not installed:
        return "not_installed"
    if configured is False:
        return "not_configured"
    if version is None and configured is None:
        return "unknown"
    return "available"


def _probe_stlink() -> dict[str, Any]:
    prepend_toolchain_path()
    if shutil.which("st-info") is None:
        return {
            "id": "stlink",
            "name": "st-info",
            "installed": False,
            "version": None,
            "connected": False,
            "detail": None,
        }
    try:
        r = subprocess.run(
            ["st-info", "--probe"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
            shell=False,
        )
        text = (r.stdout or "") + (r.stderr or "")
        connected = bool(text.strip()) and "No ST-LINK" not in text and "no device" not in text.lower()
        chip = None
        if "F103" in text.upper() or "stm32f1" in text.lower():
            chip = "STM32F103 detected"
        first = (text.splitlines()[:1] or [""])[0].strip() or None
        return {
            "id": "stlink",
            "name": "st-info",
            "installed": True,
            "version": chip or first,
            "connected": connected and bool(chip or first),
            "detail": first,
        }
    except (OSError, subprocess.TimeoutExpired):
        return {
            "id": "stlink",
            "name": "st-info",
            "installed": True,
            "version": "probe failed",
            "connected": False,
            "detail": "probe failed",
        }


def _probe_windows_app(exe_names: list[str], extra_paths: list[Path]) -> str | None:
    found = _which_any(exe_names)
    if found:
        return found
    for extra in extra_paths:
        if extra.is_file():
            return str(extra)
    return None


def tool_status() -> list[dict[str, Any]]:
    names = (
        ("arm-gcc", "arm-none-eabi-gcc"),
        ("make", "make"),
        ("clangd", "clangd"),
        ("cppcheck", "cppcheck"),
        ("openocd", "openocd"),
        ("git", "git"),
    )
    out: list[dict[str, Any]] = []
    for tid, cmd in names:
        ver = _run_version(cmd)
        out.append({"id": tid, "name": cmd, "installed": ver is not None, "version": ver})
    st = _probe_stlink()
    out.append({"id": st["id"], "name": st["name"], "installed": st["installed"], "version": st["version"]})
    return out


def gcc_installed() -> bool:
    prepend_toolchain_path()
    return shutil.which("arm-none-eabi-gcc") is not None


def make_installed() -> bool:
    prepend_toolchain_path()
    return shutil.which("make") is not None


def _env_item(id_: str, label: str, exe_names: list[str], version_args: list[str] | None = None) -> dict[str, Any]:
    path = _which_any(exe_names)
    version = _run_version(exe_names[0], version_args) if path else None
    if not path and len(exe_names) > 1:
        for name in exe_names[1:]:
            version = _run_version(name, version_args)
            if version:
                path = shutil.which(name)
                break
    installed = path is not None or version is not None
    return {
        "id": id_,
        "label": label,
        "status": _install_status(installed, version),
        "version": version,
        "path": path,
    }


def environment_status() -> dict[str, Any]:
    """Honest host environment probe. Missing tools are not_installed, never pass."""
    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
    cube_path = _probe_windows_app(
        ["STM32CubeMX", "stm32cubemx"],
        [
            program_files / "STMicroelectronics" / "STM32Cube" / "STM32CubeMX" / "STM32CubeMX.exe",
            program_files_x86 / "STMicroelectronics" / "STM32Cube" / "STM32CubeMX" / "STM32CubeMX.exe",
        ],
    )
    keil_path = _probe_windows_app(
        ["UV4"],
        [
            program_files_x86 / "Keil_v5" / "UV4" / "UV4.exe",
            program_files / "Keil_v5" / "UV4" / "UV4.exe",
        ],
    )
    idf_path = os.environ.get("IDF_PATH")
    idf_exe = _which_any(["idf.py"])
    items = [
        {
            "id": "os",
            "label": "OS",
            "status": "available",
            "version": f"{platform.system()} {platform.release()}",
            "path": None,
        },
        _env_item("gcc", "GCC", ["gcc"]),
        _env_item("clang", "Clang", ["clang"]),
        _env_item("arm-gcc", "ARM GCC", ["arm-none-eabi-gcc"]),
        _env_item("cmake", "CMake", ["cmake"]),
        _env_item("python", "Python", ["python", "python3"]),
        _env_item("git", "Git", ["git"]),
        {
            "id": "cubemx",
            "label": "STM32CubeMX",
            "status": _install_status(cube_path is not None, cube_path),
            "version": cube_path,
            "path": cube_path,
        },
        _env_item("openocd", "OpenOCD", ["openocd"]),
        {
            "id": "esp-idf",
            "label": "ESP-IDF",
            "status": _install_status(bool(idf_exe or idf_path), idf_exe, configured=bool(idf_path) if idf_exe or idf_path else None),
            "version": idf_path or ( _run_version("idf.py") if idf_exe else None),
            "path": idf_exe or idf_path,
        },
        _env_item("sdcc", "SDCC", ["sdcc"]),
        {
            "id": "keil",
            "label": "Keil",
            "status": _install_status(keil_path is not None, keil_path),
            "version": keil_path,
            "path": keil_path,
        },
    ]
    return {"os": platform.platform(), "items": items}


def connected_devices() -> dict[str, Any]:
    """Probe adapters and serial ports. Absence is not_detected, never Connected."""
    from app.tools.serialutil import list_ports

    st = _probe_stlink()
    probes = [
        {
            "id": "stlink",
            "label": "ST-LINK V2",
            "presence": "connected" if st.get("connected") else ("not_detected" if st.get("installed") else "unknown"),
            "detail": st.get("version") or ("st-info not installed" if not st.get("installed") else "Not Detected"),
            "installed": bool(st.get("installed")),
        },
        {
            "id": "cmsis-dap",
            "label": "CMSIS-DAP",
            "presence": "not_detected",
            "detail": "No CMSIS-DAP probe API",
            "installed": False,
        },
    ]
    ports = []
    for p in list_ports():
        ports.append(
            {
                "id": p.get("device") or "",
                "label": p.get("device") or "COM",
                "presence": "available",
                "detail": p.get("description") or "",
                "installed": True,
            }
        )
    if not ports:
        ports.append(
            {
                "id": "serial",
                "label": "Serial",
                "presence": "not_detected",
                "detail": "No serial ports",
                "installed": False,
            }
        )
    return {"probes": probes, "ports": ports}
