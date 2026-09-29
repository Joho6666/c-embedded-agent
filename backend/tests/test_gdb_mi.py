"""GDB/MI session tests: protocol parsing + fake-responder end-to-end.

The fake responder validates our client plumbing; a real interactive target
(OpenOCD gdbserver or QEMU) is NOT installed on this machine, so live
breakpoint sessions stay honestly NOT_TESTED — see docs/CURRENT_STATE.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from app.hardware.gdb_mi import (
    DebuggerSession,
    GdbMiError,
    gdb_available,
    parse_mi_line,
    parse_mi_stream,
)

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------- parsing

def test_parse_result_records():
    rec = parse_mi_line('2^done,bkpt={number="1",type="breakpoint",addr="0x0800014c",func="main"}')
    assert rec["kind"] == "result" and rec["class"] == "done" and rec["token"] == "2"
    assert rec["payload"]["bkpt"]["addr"] == "0x0800014c"
    assert rec["payload"]["bkpt"]["func"] == "main"


def test_parse_error_record_with_escaped_newline():
    rec = parse_mi_line('^error,msg="Warning:\\nCannot insert breakpoint 1."')
    assert rec["class"] == "error"
    assert rec["payload"]["msg"] == "Warning:\nCannot insert breakpoint 1."


def test_parse_async_stopped_with_frame():
    rec = parse_mi_line(
        '*stopped,reason="breakpoint-hit",disp="keep",bkptno="1",'
        'frame={addr="0x00000004",func="spin",args=[],file="tiny.c",line="2",arch="armv7-m"},'
        'thread-id="1",stopped-threads=["1"],core="0"'
    )
    assert rec["kind"] == "async-exec" and rec["class"] == "stopped"
    assert rec["payload"]["reason"] == "breakpoint-hit"
    assert rec["payload"]["frame"]["func"] == "spin"
    assert rec["payload"]["frame"]["args"] == []
    assert rec["payload"]["stopped-threads"] == ["1"]


def test_parse_exited_normally_and_running():
    assert parse_mi_line("4^running")["class"] == "running"
    rec = parse_mi_line('*stopped,reason="exited-normally"')
    assert rec["payload"]["reason"] == "exited-normally"
    assert parse_mi_line("1^connected")["class"] == "connected"


def test_parse_console_log_notify_and_prompt():
    assert parse_mi_line("(gdb) ") is None
    assert parse_mi_line("") is None
    console = parse_mi_line('~"Reading symbols from firmware.elf...\\n"')
    assert console["kind"] == "console" and console["text"] == "Reading symbols from firmware.elf...\n"
    log = parse_mi_line('&"warning: No program loaded.\\n"')
    assert log["kind"] == "log"
    notify = parse_mi_line('=breakpoint-created,bkpt={number="1"}')
    assert notify["kind"] == "notify" and notify["payload"]["bkpt"]["number"] == "1"
    stray = parse_mi_line("some random terminal line")
    assert stray["kind"] == "console"


def test_parse_stream_mixed():
    records = parse_mi_stream(
        [
            "1-target-select",
            "1^connected",
            "(gdb) ",
            "*stopped,reason=\"breakpoint-hit\",bkptno=\"1\"",
            "(gdb) ",
        ]
    )
    kinds = [r["kind"] for r in records]
    assert kinds == ["console", "result", "async-exec"]


# ---------------------------------------------------------------- session

def _dummy_elf(tmp_path: Path) -> Path:
    elf = tmp_path / "tiny.elf"
    elf.write_bytes(b"fake-elf-bytes")
    return elf


def test_session_start_rejects_missing_elf(tmp_path: Path):
    with pytest.raises(GdbMiError):
        DebuggerSession(tmp_path / "nope.elf").start()


def test_session_full_flow_against_fake_responder(tmp_path: Path):
    elf = _dummy_elf(tmp_path)
    session = DebuggerSession(elf, gdb_exe=[sys.executable, str(FIXTURES / "fake_gdb.py")], timeout=5)
    with session:
        conn = session.select_target()
        assert conn["ok"] is True

        bp = session.insert_breakpoint("spin")
        assert bp["ok"] is True and bp["addr"] == "0x00000004" and bp["func"] == "spin"

        bad = session.insert_breakpoint("main; shell evil")
        assert bad["ok"] is False  # rejected before reaching gdb

        run = session.run()
        assert run["ok"] is True
        assert run["stopped"]["reason"] == "breakpoint-hit"
        assert run["stopped"]["frame"]["func"] == "spin"

        regs = session.registers()
        assert regs["pc"] == "0x00000004" and regs["sp"] == "0x20000000"

        val = session.evaluate("counter")
        assert val["ok"] is True and val["value"] == "4"

        frames = session.backtrace()
        assert [f["frame"]["func"] for f in frames] == ["spin", "main"]

        mem = session.read_memory_bytes("0xE000ED28", 4)
        assert mem["ok"] is True and mem["contents"] == "00020000"

        assert session.delete_breakpoint("1")["ok"] is True
    # context manager exit sends -gdb-exit; process must be gone
    assert session._proc is None


def test_session_unavailable_when_gdb_missing(tmp_path: Path):
    session = DebuggerSession(_dummy_elf(tmp_path), gdb_exe="definitely-not-a-real-gdb-xyz")
    result = session.start()
    assert result["available"] is False


@pytest.mark.skipif(not gdb_available(), reason="arm-none-eabi-gdb not installed")
def test_real_gdb_starts_and_parses_banner(tmp_path: Path):
    """Real gdb binary smoke: MI banner parses; sim target connects.

    Interactive stops are not supported by this sim build — that limitation
    is documented; here we only assert the session plumbing against real gdb.
    """
    elf = FIXTURES / "gdbmi_sim" / "tiny.elf"
    if not elf.is_file():
        pytest.skip("sim fixture ELF not built yet")
    session = DebuggerSession(elf, target="sim", timeout=8)
    with session:
        conn = session.select_target()
        assert conn["ok"] is True and conn["class"] == "connected"
        names_rec = session.send("-data-list-register-names")
        result = session._result(names_rec)
        assert result["class"] == "done"
