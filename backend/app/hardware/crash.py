"""CrashEvidence — decode Cortex-M fault registers into a diagnosis.

Pure function over register values (from a probe adapter, a GDB/MI session,
or a test fixture). Input values may be ints or hex strings ("0x...").

Bit meanings: ARMv7-M ARM B1.5.x + RM0008; common embedded fault patterns
are mapped to concrete possible causes, not vague "check your code".
"""

from __future__ import annotations

from typing import Any

_UFSR = {
    16: ("UNDEFINSTR", "undefined instruction executed"),
    17: ("INVSTATE", "invalid EPSR state — classic bad function pointer or return to a non-Thumb address"),
    19: ("INVPC", "invalid PC on exception return — corrupted exception frame or wrong EXC_RETURN"),
    20: ("NOCP", "coprocessor access (e.g. FPU) with FPU not enabled"),
    24: ("UNALIGNED", "unaligned access with unaligned traps enabled"),
    25: ("DIVBYZERO", "integer divide by zero"),
}
_BFSR = {
    8: ("IBUSERR", "instruction bus error (fetch from invalid address)"),
    9: ("PRECISERR", "precise data bus error — exact faulting address in BFAR"),
    10: ("IMPRECISERR", "imprecise bus error — write buffer; address not exact"),
    11: ("UNSTKERR", "bus fault unstacking the exception frame"),
    12: ("STKERR", "bus fault stacking — stack pointer points at invalid memory (stack overflow?)"),
    15: ("BFARVALID", "BFAR holds the faulting address"),
}
_MMFSR = {
    0: ("IACCVIOL", "instruction access violation (execute from XN region)"),
    1: ("DACCVIOL", "data access violation — address in MMFAR"),
    7: ("MMARVALID", "MMFAR holds the faulting address"),
}


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text, 16) if text.lower().startswith("0x") else int(text, 0)
    except ValueError:
        return None


def decode_fault(
    cfsr: Any = None,
    hfsr: Any = None,
    mmfar: Any = None,
    bfar: Any = None,
    pc: Any = None,
    sp: Any = None,
) -> dict[str, Any]:
    c = _as_int(cfsr) or 0
    h = _as_int(hfsr) or 0
    mm = _as_int(mmfar)
    bf = _as_int(bfar)

    faults: list[str] = []
    flags: list[dict[str, Any]] = []

    def add(reg: str, bit: int, table: dict[int, tuple[str, str]]) -> None:
        if c & (1 << bit):
            name, meaning = table[bit]
            flags.append({"register": reg, "bit": bit, "name": name, "meaning": meaning})

    if h & (1 << 30):
        faults.append("HardFault (FORCED): an exception was escalated")
        flags.append({"register": "HFSR", "bit": 30, "name": "FORCED", "meaning": "fault escalated to HardFault"})
    if h & (1 << 1):
        faults.append("HardFault (VECTTBL): vector table read error")
    if h & (1 << 31):
        faults.append("HardFault (DEBUGEVT)")

    for bit in sorted(_MMFSR):
        add("MMFSR", bit, _MMFSR)
    for bit in sorted(_BFSR):
        add("BFSR", bit, _BFSR)
    for bit in sorted(_UFSR):
        add("UFSR", bit, _UFSR)

    if c & (1 << 0):
        faults.append("MemManage fault")
    if c & (1 << 8):
        faults.append("BusFault")
    if c & (1 << 16):
        faults.append("UsageFault")

    summary_parts: list[str] = []
    if c & (1 << 15) and bf is not None:
        summary_parts.append(f"precise bus fault at 0x{bf:08X}")
    elif c & (1 << 1) and c & (1 << 7) and mm is not None:
        summary_parts.append(f"MemManage data access violation at 0x{mm:08X}")
    if c & (1 << 17):
        summary_parts.append("invalid state — a jumped-to address was not Thumb or the function pointer is bogus")
    if c & (1 << 12):
        summary_parts.append("stack push failed — likely stack overflow (check stack size / deep call chain)")
    if c & (1 << 10):
        summary_parts.append("imprecise bus fault — check recently written peripherals / DMA targets")

    possible_causes: list[str] = []
    if c & (1 << 15) and bf is not None:
        if bf == 0:
            possible_causes.append("null-pointer write/word access at 0x00000000")
        elif 0x40000000 <= bf < 0x50000000:
            possible_causes.append(
                f"peripheral access at 0x{bf:08X} faulted — peripheral clock (RCC) likely not enabled"
            )
        else:
            possible_causes.append(f"invalid data address 0x{bf:08X} (bad pointer / wrong struct)")
    if c & (1 << 17):
        possible_causes.append("bad function pointer or corrupted return address (check callbacks, vtable, stack)")
    if c & (1 << 12) or c & (1 << 11):
        possible_causes.append("stack overflow — increase stack, check ISR nesting and large local arrays")
    if c & (1 << 25):
        possible_causes.append("divide by zero — guard the divisor")
    if c & (1 << 20):
        possible_causes.append("FPU instruction executed without enabling the FPU (SCB->CPACR)")
    if h & (1 << 30) and not flags:
        possible_causes.append("escalated fault with cleared fault-status bits — check debug/exception handling")

    return {
        "kind": "CrashEvidence",
        "faults": faults or (["no fault flags set (CFSR/HFSR clean)"] if cfsr is not None else []),
        "flags": flags,
        "summary": "; ".join(summary_parts) if summary_parts else None,
        "possibleCauses": possible_causes,
        "pc": _hex(pc),
        "sp": _hex(sp),
        "raw": {
            "CFSR": _hex(cfsr),
            "HFSR": _hex(hfsr),
            "MMFAR": _hex(mmfar),
            "BFAR": _hex(bfar),
        },
        "note": "diagnosis from register evidence — verify against source before patching",
    }


def _hex(value: Any) -> str | None:
    v = _as_int(value)
    return f"0x{v:08X}" if v is not None else None
