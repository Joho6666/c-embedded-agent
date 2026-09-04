from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def _print(data: dict[str, Any]) -> int:
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    status = str(data.get("status") or "").upper()
    if status in {"FAIL"}:
        return 1
    if status == "UNAVAILABLE":
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cea",
        description="C-Embedded Agent CLI — thin wrapper over CEA Core.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_inspect = sub.add_parser("inspect", help="inspect_project")
    p_inspect.add_argument("project_root")

    p_build = sub.add_parser("build", help="build_project")
    p_build.add_argument("project_root")

    sub.add_parser("mcp", help="start CEA MCP server on stdio")

    args = parser.parse_args(argv)
    if args.cmd == "mcp":
        from app.mcp.server import main as mcp_main

        mcp_main()
        return 0

    from app.core import build_project, inspect_project

    if args.cmd == "inspect":
        return _print(inspect_project(args.project_root))
    if args.cmd == "build":
        return _print(build_project(args.project_root))
    parser.error(f"unknown command {args.cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
