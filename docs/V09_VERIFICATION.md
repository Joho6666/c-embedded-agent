# v0.9 architecture verification

Baseline: `main@db3279164048b12ad08eba1e533de5297f3bdf21`.

| Gate | Status | Evidence |
|---|---|---|
| Backend Python 3.11 | PASS | 130 passed, 1 skipped (Windows symlink privilege) |
| Frontend production build | PASS | `npm ci` and Next.js production build completed |
| STM32F103 Golden | PASS | ARM GCC 13.3.1; all 11 projects produced non-empty ELF/HEX/BIN within 64 KiB Flash and 20 KiB RAM |
| Platform/Registry/Router/API safety | PASS | Included in the backend result |
| Secret/quality gates | PASS | 847 tracked paths scanned; 50 benchmark definitions validated |
| ESP32-S3 ESP-IDF 6.1 smoke | SKIPPED | Docker client exists locally but its Linux daemon and local ESP-IDF are unavailable; CI job is configured |
| ESP32-S3 flash/serial/hardware | NOT RUN | No detected ESP32-S3 device |
| STM32 hardware | NOT RUN | No probe or serial hardware used |
| Agent vs Plain LLM benchmark | SKIPPED | LLM configuration unavailable; unexecuted metrics are `null` |

The application and package versions remain `0.8.0-beta`. The architecture target is not promoted to `0.9.0-beta` until the remaining release gates have real evidence.
