from __future__ import annotations

from pathlib import Path, PurePosixPath


class PathEscapeError(ValueError):
    pass


class ProtectedPathError(ValueError):
    pass


ALLOWED_WRITE_PREFIXES = ("Core/Src/", "Core/Inc/", "App/", "User/")
FORBIDDEN_WRITE = (
    "Drivers/",
    "Middlewares/",
    "startup",
    ".ld",
    ".ioc",
    "Makefile",
    "makefile",
)


def resolve_in_root(root: Path, rel: str) -> Path:
    root = root.resolve()
    raw = (root / rel).resolve()
    if raw != root and root not in raw.parents:
        raise PathEscapeError(f"path escapes workspace: {rel}")
    return raw


def normalize_rel(rel: str) -> str:
    p = str(PurePosixPath(rel.replace("\\", "/"))).lstrip("./")
    if p.startswith("../") or p == "..":
        raise PathEscapeError(f"path escapes workspace: {rel}")
    return p


def assert_writable(rel: str, *, advanced: bool = False) -> str:
    norm = normalize_rel(rel)
    if advanced:
        return norm
    low = norm.lower()
    name = PurePosixPath(norm).name
    if name.lower() == "makefile" or low.endswith(".ld") or low.endswith(".ioc") or name.lower().startswith("startup"):
        raise ProtectedPathError(f"protected file: {norm}")
    if any(
        norm.startswith(p) or norm.startswith(p.rstrip("/"))
        for p in ("Drivers/", "Drivers", "Middlewares/", "Middlewares")
    ):
        raise ProtectedPathError(f"protected path: {norm}")
    if not any(norm.startswith(p) or norm == p.rstrip("/") for p in ALLOWED_WRITE_PREFIXES):
        # allow files directly under Core/Inc or Core/Src without trailing extra
        if not (norm.startswith("Core/Src/") or norm.startswith("Core/Inc/") or norm.startswith("App/") or norm.startswith("User/")):
            raise ProtectedPathError(f"write not allowed: {norm}")
    return norm
