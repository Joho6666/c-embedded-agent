# Agent Runtime Rules

- Keep one runtime lifecycle. Routing, tools, skills, context, and platforms are collaborators, not duplicate runtimes.
- The router decides the workflow and allowed tools before model execution. Emit auditable routing facts, never hidden chain-of-thought.
- `plan` is read-only. `code` requires approval for every workspace write. `auto` writes only standard paths. `advanced` still protects guarded paths. Device tools always require explicit hardware intent and separate approval.
- Replace the current routed context each turn; do not append it indefinitely. Preserve `IOC > project.json > board profile > adapter defaults`.
- Success requires build/validation/device evidence appropriate to the requested task. Absence of evidence cannot be converted to PASS.
