# Architecture

## Request path

`Intent -> TaskClassifier -> Workflow/Skill/Context Router -> Planner -> Runtime -> ToolRegistry -> PlatformRegistry -> Adapter operations`.

The runtime remains responsible for run state, persistence, cancellation, approval and SSE. Registries are the only extension boundary. Platform adapters own vendor and board knowledge and return structured results with status, diagnostics, artifacts and evidence.

## Stable contracts

- Explicit project creation resolves `platform`, `mcu`, `framework`, optional `board` and `adapterId`. Import detection rejects conflicts and unknown platforms.
- Context levels are FOCUSED (12K chars, one skill), PROJECT (24K, two skills), and DEEP (48K, four skills by default).
- Tool specs combine JSON schema, handler, effect, availability and approval policy.
- Existing routes and tool names remain compatible. `/api/platforms` and the `routing` SSE event are additive.

See `docs/INDEX.md` for detailed contracts and ADRs.
