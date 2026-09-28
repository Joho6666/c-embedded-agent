#!/usr/bin/env python3
"""Launcher for the C-Embedded MCP server (stdio). Point your harness at this file:

    python /path/to/c-embedded-agent/scripts/cea_mcp.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.mcp_server import main  # noqa: E402

if __name__ == "__main__":
    main()
