from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.types import FAIL, HARDWARE_ACTION, PARTIAL, PASS, UNKNOWN, UNAVAILABLE, envelope
from app.tools.hardware_run import run_pipeline
from app.validation import hardware_status


def validate_hardware_at(
    root: Path,
    *,
    serial_device: str | None = None,
    baud: int = 115200,
    expect: str | None = None,
    task: str = "",
    run_full_pipeline: bool = True,
) -> dict[str, Any]:
    if run_full_pipeline:
        pipeline = run_pipeline(
            root,
            serial_device=serial_device,
            baud=baud,
            expect=expect,
            task=task,
        )
        validation = pipeline.get("validation") or {}
        status = str(validation.get("status") or UNKNOWN).upper()
        if status not in {PASS, FAIL, PARTIAL, UNKNOWN, UNAVAILABLE}:
            status = UNKNOWN
        if status == PASS and not serial_device and not _pipeline_has_probe(pipeline):
            # Never promote compile-only success to hardware PASS.
            status = UNAVAILABLE
            validation = {**validation, "status": status, "reason": "Hardware Not Tested"}
        pipeline = {**pipeline, "validation": validation}
        return envelope(
            status=status,  # type: ignore[arg-type]
            side_effect=HARDWARE_ACTION,
            hardware_status=status,
            software_build_passed=_build_passed(pipeline),
            hardware_passed=status == PASS,
            reason=validation.get("reason") or validation.get("observed"),
            validation=validation,
            steps=pipeline.get("steps") or [],
            pipeline=pipeline,
            available=pipeline.get("available"),
        )

    hw = hardware_status(
        serial_lines=None,
        expect=expect,
        task=task or "led",
        has_probe=False,
    )
    status = str(hw.get("status") or UNAVAILABLE).upper()
    return envelope(
        status=status if status in {PASS, FAIL, PARTIAL, UNKNOWN, UNAVAILABLE} else UNKNOWN,  # type: ignore[arg-type]
        side_effect=HARDWARE_ACTION,
        hardware_status=status,
        software_build_passed=False,
        hardware_passed=False,
        reason=hw.get("reason") or "Hardware Not Tested",
        validation=hw,
        steps=[],
        available=False,
    )


def _build_passed(pipeline: dict[str, Any]) -> bool:
    for step in pipeline.get("steps") or []:
        if step.get("kind") == "build" and step.get("status") in {"success", "SUCCESS", "PASS"}:
            return True
    return False


def _pipeline_has_probe(pipeline: dict[str, Any]) -> bool:
    for step in pipeline.get("steps") or []:
        if step.get("kind") in {"flash", "detect"} and step.get("status") in {"success", "SUCCESS"}:
            return True
    return False
