# Platform Adapters

Adapters describe capabilities, detect/import/create projects, expose protected paths, and implement build, clean, flash, reset, serial, generation and validation. Registry resolution is explicit for creation and evidence-based for imports. Conflicting evidence returns `ambiguous`; missing registration returns `unsupported`.

An adapter is `ready` only when its contract tests and real build smoke pass. `experimental` capabilities are visible but must not be presented as production-ready. Device capability does not imply a connected device.
