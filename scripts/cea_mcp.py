"""Launch CEA MCP Server (stdio) from the repository root."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.mcp.server import main  # noqa: E402

if __name__ == "__main__":
    main()
