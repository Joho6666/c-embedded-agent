# Platform Adapter Rules

- Generic code must not contain board pins, vendor commands, MCU defaults, or platform-specific validators.
- An adapter owns detection, templates, build/clean, flash/reset/serial, generators, validation, protected paths, skills, and knowledge roots for its platform.
- Detection conflicts are `ambiguous`; unknown identifiers are `unsupported`. Never use a default adapter after failed resolution.
- Keep operation results structured and evidence-bearing. Device absence is `UNAVAILABLE`; hardware not exercised is `SKIPPED` or `NOT RUN`.
- Add adapter contract tests and one real build smoke test before marking an adapter `ready`.
