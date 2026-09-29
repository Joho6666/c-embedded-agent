"""GDB/MI DebuggerSession — machine-interface debugging, not terminal scraping.

Speaks GDB/MI (`gdb -q -i=mi`) against a target:

- `sim`     — the arm-none-eabi-gdb built-in ARM simulator. Works without
              hardware; HAL-heavy firmwares exit early there (the sim has no
              peripherals), so sim runs are validated with minimal ELFs.
              Evidence level: SIMULATION.
- `remote`  — OpenOCD's gdbserver (`openocd ... -c "gdb_port 3333"`).
              Evidence level: DEBUGGER (real hardware).

All responses are MI records (`^done`, `^error`, `*stopped`, `=breakpoint-*`).
No human-format parsing anywhere.
"""

from __future__ import annotations

import itertools
import queue
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from app.tools.toolchain import prepend_toolchain_path

_PROMPT = "(gdb)"


class GdbMiError(RuntimeError):
    pass


# ---------------------------------------------------------------- MI parsing

_ESCAPES = {"n": "\n", "r": "\r", "t": "\t", '"': '"', "\\": "\\", "'": "'"}


def _parse_value(text: str, pos: int) -> tuple[Any, int]:
    """Parse one MI value (c-string / tuple / list / constant) starting at pos."""
    while pos < len(text) and text[pos] in " \t":
        pos += 1
    if pos >= len(text):
        return None, pos
    ch = text[pos]
    if ch == '"':
        pos += 1
        out: list[str] = []
        while pos < len(text):
            c = text[pos]
            if c == "\\" and pos + 1 < len(text):
                out.append(_ESCAPES.get(text[pos + 1], text[pos + 1]))
                pos += 2
                continue
            if c == '"':
                pos += 1
                break
            out.append(c)
            pos += 1
        return "".join(out), pos
    if ch == "{":
        pos += 1
        obj: dict[str, Any] = {}
        while pos < len(text) and text[pos] != "}":
            key, pos = _parse_word(text, pos)
            while pos < len(text) and text[pos] in " \t":
                pos += 1
            if pos < len(text) and text[pos] == "=":
                pos += 1
            value, pos = _parse_value(text, pos)
            obj[key] = value
            while pos < len(text) and text[pos] in " \t,":
                pos += 1
        return obj, min(pos + 1, len(text))
    if ch == "[":
        pos += 1
        items: list[Any] = []
        while pos < len(text) and text[pos] != "]":
            value, pos = _parse_value(text, pos)
            while pos < len(text) and text[pos] in " \t":
                pos += 1
            if isinstance(value, str) and value.endswith("="):
                # gdb result-items inside lists: `frame={...},frame={...}`
                inner, pos = _parse_value(text, pos)
                value = {value[:-1]: inner}
            items.append(value)
            while pos < len(text) and text[pos] in " \t,":
                pos += 1
        return items, min(pos + 1, len(text))
    m = re.match(r"[^\",{}\[\]]+", text[pos:])
    word = (m.group(0).strip() if m else "").strip()
    if not word:
        # Unparseable char — consume it so callers can never stall on us.
        return None, pos + 1
    return word, pos + len(word)


def _parse_word(text: str, pos: int) -> tuple[str, int]:
    while pos < len(text) and text[pos] in " \t":
        pos += 1
    m = re.match(r"[^=,{}\[\] \t]+", text[pos:])
    word = m.group(0) if m else ""
    return word, pos + len(word)


def _parse_results(text: str) -> dict[str, Any]:
    """Parse an MI result list: comma-separated key=value assignments."""
    result: dict[str, Any] = {}
    pos = 0
    while pos < len(text):
        mark = pos
        while pos < len(text) and text[pos] in " \t,":
            pos += 1
        if pos >= len(text):
            break
        key, pos = _parse_word(text, pos)
        while pos < len(text) and text[pos] in " \t":
            pos += 1
        if pos < len(text) and text[pos] == "=":
            pos += 1
        value, pos = _parse_value(text, pos)
        result[key] = value
        if pos <= mark:
            # Malformed fragment (e.g. stray brace) — skip one char, never stall.
            pos = mark + 1
    return result


def parse_mi_line(line: str) -> dict[str, Any] | None:
    """Parse one MI output line into a record dict, or None for prompts."""
    line = line.rstrip("\r\n")
    if not line or line.strip().startswith(_PROMPT):
        return None
    m = re.match(r"(\d*)([\^\*\+=&~@])(.*)$", line)
    if not m:
        return {"kind": "console", "text": line}
    token, marker, rest = m.groups()
    kinds = {"^": "result", "*": "async-exec", "+": "async-status", "=": "notify", "&": "log", "~": "console", "@": "target"}
    kind = kinds[marker]
    rec: dict[str, Any] = {"kind": kind, "raw": line}
    if token:
        rec["token"] = token
    if marker in "~&@":
        val, _ = _parse_value(rest, 0)
        rec["text"] = val if isinstance(val, str) else rest
        return rec
    cls, _, payload = rest.partition(",")
    rec["class"] = cls.strip()
    if payload:
        rec["payload"] = _parse_results(payload)
    return rec


def parse_mi_stream(lines: list[str]) -> list[dict[str, Any]]:
    return [r for r in (parse_mi_line(l) for l in lines) if r]


# ---------------------------------------------------------------- session

class DebuggerSession:
    """One gdb process. Use as a context manager; always stop() when done.

    A background reader thread feeds a line queue, so both real gdb timing
    (async ``*stopped`` after the prompt) and scripted responders (stopped
    before the prompt) are handled. Reads are timeout-guarded: targets that
    never stop need an external interrupt — not used by supported flows.
    """

    RESULT_CLASSES = ("done", "error", "running", "connected", "exit")

    def __init__(
        self,
        elf: str | Path,
        target: str = "sim",  # "sim" | "remote:<host:port>"
        timeout: float = 10.0,
        gdb_exe: str | list[str] | tuple[str, ...] | None = None,
    ) -> None:
        self.elf = str(elf)
        self.target = target
        self.timeout = timeout
        self.gdb_exe = gdb_exe
        self._proc: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()
        self._tokens = itertools.count(1)
        self._lines: "queue.Queue[str]" = queue.Queue()
        self._reader: threading.Thread | None = None

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> dict[str, Any]:
        if not Path(self.elf).is_file():
            raise GdbMiError(f"ELF not found: {self.elf}")
        if isinstance(self.gdb_exe, (list, tuple)):
            argv = [*self.gdb_exe, "-q", "-i=mi", "--nx", self.elf]
        else:
            exe = self.gdb_exe or shutil.which("arm-none-eabi-gdb")
            if not exe:
                prepend_toolchain_path()
                exe = shutil.which("arm-none-eabi-gdb")
            if not exe:
                return {"available": False, "status": "UNAVAILABLE", "reason": "arm-none-eabi-gdb not installed"}
            argv = [exe, "-q", "-i=mi", "--nx", self.elf]
        try:
            self._proc = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
            )
        except OSError as e:
            return {"available": False, "status": "UNAVAILABLE", "reason": f"gdb failed to start: {e}"}
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        self._drain_to_prompt()
        return {"available": True, "status": "SUCCESS", "target": self.target}

    def _read_loop(self) -> None:
        assert self._proc and self._proc.stdout
        try:
            for line in iter(self._proc.stdout.readline, ""):
                if not line:
                    break
                self._lines.put(line)
        except Exception:  # noqa: BLE001 — reader dies with the process
            pass

    def stop(self) -> None:
        if self._proc is not None:
            try:
                if self._proc.stdin:
                    self._proc.stdin.write("-gdb-exit\n")
                    self._proc.stdin.flush()
                self._proc.wait(timeout=5)
            except Exception:  # noqa: BLE001 — best-effort teardown
                self._proc.kill()
            self._proc = None

    def __enter__(self) -> "DebuggerSession":
        started = self.start()
        if not started.get("available"):
            raise GdbMiError(started.get("reason") or "gdb unavailable")
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()

    # -- MI plumbing ---------------------------------------------------------

    def _get_line(self, timeout: float) -> str:
        try:
            return self._lines.get(timeout=timeout)
        except queue.Empty:
            raise GdbMiError(f"timeout waiting for gdb MI output ({timeout:.1f}s)") from None

    def _drain_to_prompt(self) -> None:
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            line = self._get_line(deadline - time.time())
            if line.strip().startswith(_PROMPT):
                return
        raise GdbMiError("timeout waiting for initial gdb MI prompt")

    def send(self, command: str) -> list[dict[str, Any]]:
        """Send one MI command; read records until the next (gdb) prompt."""
        if self._proc is None or self._proc.poll() is not None:
            raise GdbMiError("gdb session is not running")
        with self._lock:
            tok = str(next(self._tokens))
            assert self._proc.stdin is not None
            # command carries its leading dash; wire format is `<token>-<cmd>`
            self._proc.stdin.write(f"{tok}{command if command.startswith('-') else '-' + command}\n")
            self._proc.stdin.flush()
            records: list[dict[str, Any]] = []
            deadline = time.time() + self.timeout
            while True:
                line = self._get_line(deadline - time.time())
                if line.strip().startswith(_PROMPT):
                    break
                rec = parse_mi_line(line)
                if rec is not None:
                    rec.setdefault("token", tok)
                    records.append(rec)
            return records

    def _result(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        for r in records:
            if r["kind"] == "result":
                return r
        return {"kind": "result", "class": "error", "payload": {"msg": "no result record"}}

    def _extract_stopped(self, records: list[dict[str, Any]]) -> dict[str, Any] | None:
        for r in records:
            if r["kind"] == "async-exec" and r.get("class") == "stopped":
                return r.get("payload") or {"reason": "stopped"}
        return None

    def _wait_stopped(self, max_s: float | None = None) -> dict[str, Any] | None:
        """Read async output until a *stopped record arrives (timeout-guarded)."""
        deadline = time.time() + (max_s or self.timeout)
        while time.time() < deadline:
            try:
                line = self._lines.get(timeout=deadline - time.time())
            except queue.Empty:
                break
            rec = parse_mi_line(line)
            if rec and rec["kind"] == "async-exec" and rec.get("class") == "stopped":
                return rec.get("payload") or {"reason": "stopped"}
        return None

    # -- high-level ops ------------------------------------------------------

    def select_target(self) -> dict[str, Any]:
        tgt = "sim" if self.target == "sim" else self.target.split(":", 1)[1]
        r = self._result(self.send(f"-target-select {tgt}"))
        ok = r.get("class") == "connected"
        return {"available": True, "ok": ok, "class": r.get("class"), "reason": (r.get("payload") or {}).get("msg")}

    def download(self) -> dict[str, Any]:
        r = self._result(self.send("-target-download"))
        return {"available": True, "ok": r.get("class") == "done", "class": r.get("class")}

    def insert_breakpoint(self, location: str) -> dict[str, Any]:
        safe = str(location).strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*|\*?0x[0-9A-Fa-f]+", safe):
            return {"available": True, "ok": False, "reason": "invalid breakpoint location"}
        r = self._result(self.send(f"-break-insert {safe}"))
        payload = r.get("payload") or {}
        if r.get("class") == "done":
            bkpt = payload.get("bkpt") or {}
            return {
                "available": True,
                "ok": True,
                "number": bkpt.get("number"),
                "addr": bkpt.get("addr"),
                "func": bkpt.get("func"),
            }
        return {"available": True, "ok": False, "reason": payload.get("msg")}

    def delete_breakpoint(self, number: str) -> dict[str, Any]:
        r = self._result(self.send(f"-break-delete {number}"))
        return {"available": True, "ok": r.get("class") == "done"}

    def run(self) -> dict[str, Any]:
        records = self.send("-exec-run")
        r = self._result(records)
        if r.get("class") not in ("running", "done"):
            return {"available": True, "ok": False, "reason": (r.get("payload") or {}).get("msg")}
        stopped = self._extract_stopped(records) or self._wait_stopped()
        return {"available": True, "ok": True, "stopped": stopped}

    def continue_(self) -> dict[str, Any]:
        records = self.send("-exec-continue")
        r = self._result(records)
        if r.get("class") != "running":
            return {"available": True, "ok": False, "reason": (r.get("payload") or {}).get("msg")}
        stopped = self._extract_stopped(records) or self._wait_stopped()
        return {"available": True, "ok": True, "stopped": stopped}

    def step(self) -> dict[str, Any]:
        records = self.send("-exec-step")
        r = self._result(records)
        if r.get("class") != "running":
            return {"available": True, "ok": False, "reason": (r.get("payload") or {}).get("msg")}
        stopped = self._extract_stopped(records) or self._wait_stopped()
        return {"available": True, "ok": True, "stopped": stopped}

    def registers(self) -> dict[str, str]:
        names_rec = self._result(self.send("-data-list-register-names"))
        names = ((names_rec.get("payload") or {}).get("register-names")) or []
        if not names:
            return {}
        vals = self._result(self.send("-data-list-register-values x"))
        out: dict[str, str] = {}
        for entry in (vals.get("payload") or {}).get("register-values") or []:
            idx, val = entry.get("number"), entry.get("value")
            if idx is not None and str(idx).isdigit() and int(idx) < len(names):
                out[str(names[int(idx)])] = str(val)
        return out

    def read_memory_bytes(self, address: str, count: int) -> dict[str, Any]:
        if not re.fullmatch(r"0x[0-9A-Fa-f]+", address) or not 0 < count <= 1024:
            return {"available": True, "ok": False, "reason": "invalid address or count"}
        r = self._result(self.send(f"-data-read-memory-bytes {address} {count}"))
        if r.get("class") == "done":
            mem = (r.get("payload") or {}).get("memory") or []
            contents = mem[0].get("contents") if mem else None
            return {"available": True, "ok": contents is not None, "address": address, "contents": contents}
        return {"available": True, "ok": False, "reason": (r.get("payload") or {}).get("msg")}

    def evaluate(self, expression: str) -> dict[str, Any]:
        safe = expression.strip()
        if not safe or any(c in safe for c in "\n;"):
            return {"available": True, "ok": False, "reason": "invalid expression"}
        r = self._result(self.send(f"-data-evaluate-expression {safe}"))
        if r.get("class") == "done":
            return {"available": True, "ok": True, "value": (r.get("payload") or {}).get("value")}
        return {"available": True, "ok": False, "reason": (r.get("payload") or {}).get("msg")}

    def backtrace(self) -> list[dict[str, Any]]:
        r = self._result(self.send("-stack-list-frames"))
        stack = (r.get("payload") or {}).get("stack")
        return stack if isinstance(stack, list) else []


def gdb_available() -> bool:
    exe = shutil.which("arm-none-eabi-gdb")
    if not exe:
        prepend_toolchain_path()
        exe = shutil.which("arm-none-eabi-gdb")
    return exe is not None
