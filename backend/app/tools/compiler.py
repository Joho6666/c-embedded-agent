from __future__ import annotations

import asyncio
import shutil
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from app.config.settings import settings
from app.tools.gcc_parser import parse_gcc_output
from app.tools.toolchain import prepend_toolchain_path

LineCallback = Callable[[str, str], Awaitable[None] | None]


class CompileError(RuntimeError):
    pass


def compile_project(project_root: Path) -> dict[str, Any]:
    prepend_toolchain_path()
    make = shutil.which("make")
    gcc = shutil.which("arm-none-eabi-gcc")
    if not gcc:
        raise CompileError("未检测到 arm-none-eabi-gcc，无法真实编译。")
    if not make:
        raise CompileError("未检测到 make，无法真实编译。")

    root = project_root.resolve()
    import subprocess

    proc = subprocess.run(
        [make, "-j4"],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=settings.compile_timeout_sec,
        check=False,
        shell=False,
    )
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return _pack(root, proc.returncode, proc.stdout or "", proc.stderr or "", combined)


async def compile_project_streaming(
    project_root: Path,
    on_line: LineCallback | None = None,
) -> dict[str, Any]:
    prepend_toolchain_path()
    make = shutil.which("make")
    gcc = shutil.which("arm-none-eabi-gcc")
    if not gcc:
        raise CompileError("未检测到 arm-none-eabi-gcc，无法真实编译。")
    if not make:
        raise CompileError("未检测到 make，无法真实编译。")

    root = project_root.resolve()
    proc = await asyncio.create_subprocess_exec(
        make,
        "-j4",
        cwd=str(root),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []

    async def _pump(stream: asyncio.StreamReader, name: str, bucket: list[str]) -> None:
        while True:
            raw = await stream.readline()
            if not raw:
                break
            line = raw.decode("utf-8", errors="replace").rstrip("\n")
            bucket.append(line)
            if on_line:
                maybe = on_line(name, line)
                if asyncio.iscoroutine(maybe):
                    await maybe

    await asyncio.wait_for(
        asyncio.gather(
            _pump(proc.stdout, "stdout", stdout_chunks),  # type: ignore[arg-type]
            _pump(proc.stderr, "stderr", stderr_chunks),  # type: ignore[arg-type]
        ),
        timeout=settings.compile_timeout_sec,
    )
    code = await proc.wait()
    stdout = "\n".join(stdout_chunks)
    stderr = "\n".join(stderr_chunks)
    combined = stdout + "\n" + stderr
    return _pack(root, code or 0, stdout, stderr, combined)


def _pack(root: Path, code: int, stdout: str, stderr: str, combined: str) -> dict[str, Any]:
    if len(combined.encode()) > settings.max_stdout_bytes:
        combined = combined[: settings.max_stdout_bytes]
    diagnostics = parse_gcc_output(combined)
    artifacts = []
    for name in ("firmware.elf", "firmware.hex", "firmware.bin", "firmware.map"):
        p = root / name
        if p.is_file():
            artifacts.append({"name": name, "path": name, "size": p.stat().st_size})
    size = _size(root) if (root / "firmware.elf").is_file() else None
    return {
        "success": code == 0,
        "exit_code": code,
        "stdout": stdout,
        "stderr": stderr,
        "combined": combined,
        "diagnostics": diagnostics,
        "artifacts": artifacts,
        "memory": size,
    }


def _size(project_root: Path) -> dict[str, int] | None:
    exe = shutil.which("arm-none-eabi-size")
    if not exe:
        return None
    import subprocess

    r = subprocess.run(
        [exe, "firmware.elf"],
        cwd=str(project_root.resolve()),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        shell=False,
    )
    lines = [ln for ln in (r.stdout or "").splitlines() if ln.strip()]
    if len(lines) < 2:
        return None
    parts = lines[-1].split()
    if len(parts) < 3:
        return None
    text, data, bss = int(parts[0]), int(parts[1]), int(parts[2])
    return {"text": text, "data": data, "bss": bss, "flash": text + data, "ram": data + bss}
