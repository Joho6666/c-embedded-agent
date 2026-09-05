# Hardware Testing

Device work requires explicit intent and separate approval. A hardware result records platform, adapter, command, device identity, firmware artifact, serial/probe evidence and status. Empty output, missing OpenOCD/port/board, or error tokens cannot pass.

Allowed statuses are `PASS`, `FAIL`, `PARTIAL`, `UNKNOWN`, `UNAVAILABLE`, `SKIPPED`, and `NOT RUN`. CI never flashes hardware. Concurrent projects must keep independent hardware sessions.
