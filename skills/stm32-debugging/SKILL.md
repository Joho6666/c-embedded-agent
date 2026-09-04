---
name: stm32-debugging
description: Deterministic STM32F103 debug loop. Compile pass is not hardware pass.
---

# STM32 Debugging

## When
Build failed, device silent, or "it compiled so it must work".

## Recommended flow
inspect_project → parse_ioc → build_project → diagnose_build → apply a **minimal** fix → build_project → flash_firmware → read_serial → validate_hardware

## Forbidden
- Recreating the project on first failure.
- Editing Drivers / startup / linker / Makefile unless Error Memory mechanical fix requires Makefile HAL module lines.
- Disabling features to hide errors.
- Equating build SUCCESS with hardware PASS.
- Unlimited flash loops (Core process budget applies).
- Every change must have a stated reason.

## Verify
diagnose_build uses gcc/ld + Error Memory first. LLM is optional commentary, never the only diagnosis.

## Common errors
Missing HAL module, undef IRQ, include path, F4 API on F1, pin conflict.

## Failure
After a few mechanical retries, stop and report FAIL/UNAVAILABLE with logs.

## Done
Either a explained fix + honest hardware status, or a structured stop with evidence.
