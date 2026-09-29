"""Fake GDB/MI responder for protocol-level DebuggerSession tests.

Emulates the MI record stream of a gdb session against a scripted target,
matching real gdb timing: the result record + prompt arrive synchronously,
while `*stopped` arrives asynchronously (no prompt).

This validates the client (session plumbing + parsing) — it is NOT a
hardware or simulator test; real-target validation requires OpenOCD/QEMU
and is marked NOT_TESTED until a probe is available.
"""

import sys
import threading
import time

STOPPED_RECORD = (
    '*stopped,reason="breakpoint-hit",disp="keep",bkptno="1",'
    'frame={addr="0x00000004",func="spin",args=[],file="tiny.c",line="2",'
    'arch="armv7-m"},thread-id="1",stopped-threads=["1"],core="0"'
)


def out(line: str) -> None:
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def emit_async_stopped(delay: float = 0.05) -> None:
    def worker() -> None:
        time.sleep(delay)
        out(STOPPED_RECORD)

    threading.Thread(target=worker, daemon=True).start()


def main() -> None:
    out("=thread-group-added,id=\"i1\"")
    out("(gdb) ")
    for raw in sys.stdin:
        line = raw.strip()
        if not line or "-" not in line:
            continue
        token, _, cmd = line.partition("-")
        cmd = cmd.strip()

        if cmd.startswith("target-select"):
            out(f"{token}^connected")
        elif cmd.startswith("target-download") or cmd.startswith("target-attach"):
            out(f"{token}^done")
        elif cmd.startswith("break-insert"):
            out(
                f'{token}^done,bkpt={{number="1",type="breakpoint",disp="keep",enabled="y",'
                'addr="0x00000004",func="spin",file="tiny.c",line="2",times="0",'
                'original-location="spin"}'
            )
        elif cmd.startswith("break-delete"):
            out(f"{token}^done")
        elif cmd.startswith("exec-run") or cmd.startswith("exec-continue") or cmd.startswith("exec-step"):
            out(f"{token}^running")
            out("(gdb) ")
            emit_async_stopped()
            continue  # prompt already sent; no second prompt
        elif cmd.startswith("data-list-register-names"):
            out(f'{token}^done,register-names=["r0","r1","sp","lr","pc","xpsr"]')
        elif cmd.startswith("data-list-register-values"):
            out(
                f'{token}^done,register-values=['
                '{number="0",value="0x0"},{number="1",value="0x0"},'
                '{number="2",value="0x20000000"},{number="3",value="0x0000001d"},'
                '{number="4",value="0x00000004"},{number="5",value="0x01000000"}]'
            )
        elif cmd.startswith("data-evaluate-expression"):
            out(f'{token}^done,value="4"')
        elif cmd.startswith("data-read-memory-bytes"):
            out(f'{token}^done,memory=[{{begin="0xe000ed28",contents="00020000",endaddr="0xe000ed2c"}}]')
        elif cmd.startswith("stack-list-frames"):
            out(
                f'{token}^done,stack=['
                'frame={level="0",addr="0x00000004",func="spin",file="tiny.c",line="2",arch="armv7-m"},'
                'frame={level="1",addr="0x0000001c",func="main",file="tiny.c",line="6",arch="armv7-m"}]'
            )
        elif cmd.startswith("gdb-exit"):
            out(f"{token}^exit")
            return
        else:
            out(f'{token}^error,msg="No symbol or unknown command"')
        out("(gdb) ")


if __name__ == "__main__":
    main()
