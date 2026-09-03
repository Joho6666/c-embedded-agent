# ADR 0001: Platform adapter boundary

Status: Accepted.

Platform-specific project, toolchain, device and validation behavior belongs to one registered adapter. Generic runtime code depends only on the adapter contract. This prevents new platforms from multiplying runtimes or leaking STM32 defaults into detection and execution.
