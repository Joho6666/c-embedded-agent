"""Peripheral evidence requirements — what 'proven on hardware' means per task.

Each peripheral defines the minimum acceptable evidence. Compile success,
code inspection or LLM confidence are never acceptable evidence anywhere.

Methods vocabulary:
- serial-token          literal token received from the device (CEA:USART:PASS …)
- serial-value          serial line with a parsed value in range (CEA:ADC:value=N)
- gpio-probe            external GPIO probe observed the pin toggle
- debugger-register     debugger read of the peripheral/CPU register proves it
- logic-analyzer        LA measured frequency/duty/edges
- user-confirm          explicit human confirmation (WAITING_FOR_USER resolved)
- device-response       peripheral ACK/response (I2C ACK, SPI loopback echo)
"""

from __future__ import annotations

from typing import Any

# method weights: evidence quality ordering used to explain shortfalls
METHODS = {
    "serial-token": "expected token received over the serial line",
    "serial-value": "expected value read over serial and in range",
    "gpio-probe": "external probe observed the physical pin change",
    "debugger-register": "peripheral/CPU register sampled via debugger",
    "logic-analyzer": "logic analyzer measured the waveform",
    "user-confirm": "human confirmed the physical behavior",
    "device-response": "peripheral ACK/response observed",
}

REQUIREMENTS: dict[str, dict[str, Any]] = {
    "led": {
        "minimum": "compile success is never hardware evidence",
        "any_of": [
            ["gpio-probe"],
            ["debugger-register"],
            ["user-confirm"],
        ],
        "note": "GPIO toggle must be observed, not inferred from code",
    },
    "pwm": {
        "minimum": "frequency and duty cycle measured",
        "any_of": [
            ["logic-analyzer"],
            ["debugger-register"],  # TIMx_CNT/CCR1 sampling
        ],
        "note": "timer register evidence accepted at SIMULATION/HW boundary; PARTIAL without LA",
    },
    "usart": {
        "minimum": "token received",
        "any_of": [
            ["serial-token"],
        ],
        "note": "CEA:USART:PASS must be really received",
    },
    "adc": {
        "minimum": "value in range with variation/stability",
        "any_of": [
            ["serial-value"],
            ["debugger-register"],  # ADC1_DR sampling
        ],
        "note": "0–4095 with observed variation",
    },
    "i2c": {
        "minimum": "device ACK",
        "any_of": [
            ["device-response"],
            ["debugger-register"],  # I2C1_SR1 ACK flag
        ],
        "note": "address ACK + transaction",
    },
    "spi": {
        "minimum": "transaction/loopback echo",
        "any_of": [
            ["device-response"],
            ["debugger-register"],
        ],
        "note": "loopback echo or known peripheral response",
    },
    "exti": {
        "minimum": "actual signal change handled",
        "any_of": [
            ["serial-token"],
            ["gpio-probe"],
            ["user-confirm"],
        ],
        "note": "button press must produce an observable effect",
    },
    "gpio_input": {
        "minimum": "actual signal change observed",
        "any_of": [
            ["gpio-probe"],
            ["user-confirm"],
            ["serial-token"],
        ],
        "note": "calling HAL_GPIO_ReadPin in code proves nothing",
    },
}


def evaluate_peripheral(peripheral: str, evidence: list[dict[str, Any]]) -> dict[str, Any]:
    """Check collected evidence against the peripheral's requirement.

    `evidence` items look like EvidenceRecords with a `method` field.
    Status: PASS (requirement met) / NOT_TESTED (no qualifying evidence) /
    PARTIAL (some evidence but below the bar, e.g. register-only where LA is
    expected) / FAIL (contradicting evidence present).
    """
    req = REQUIREMENTS.get(peripheral)
    if req is None:
        return {"peripheral": peripheral, "status": "NOT_TESTED", "reason": "no evidence requirement defined"}

    methods = [str(e.get("method") or "") for e in evidence]
    failed = [e for e in evidence if e.get("passed") is False]
    if failed:
        return {
            "peripheral": peripheral,
            "status": "FAIL",
            "reason": "contradicting evidence present",
            "failedClaims": [e.get("claim") for e in failed],
        }

    met = None
    for combo in req.get("any_of") or []:
        if all(m in methods for m in combo):
            met = combo
            break
    if met:
        return {"peripheral": peripheral, "status": "PASS", "metBy": met, "note": req.get("note")}

    partial_methods = [m for m in methods if m in METHODS]
    return {
        "peripheral": peripheral,
        "status": "NOT_TESTED" if not partial_methods else "PARTIAL",
        "requirement": req.get("minimum"),
        "note": req.get("note"),
        "missing": req.get("any_of"),
        "collectedMethods": partial_methods,
    }
