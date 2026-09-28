from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class WriteScope:
    """Paths an agent may write by default for one platform layout.

    ``prefixes`` are directory prefixes (``Core/Src/``); ``root_suffixes`` allow
    files directly in the project root (``main.c`` for flat 8051 projects);
    ``protected`` are exact paths or directory prefixes that stay read-only.
    """

    prefixes: tuple[str, ...] = ALLOWED_WRITE_PREFIXES
    root_suffixes: tuple[str, ...] = ()
    protected: tuple[str, ...] = ()

    def is_protected(self, norm: str) -> bool:
        return any(norm == item or norm.startswith(item.rstrip("/") + "/") for item in self.protected)

    def allows(self, norm: str) -> bool:
        if self.is_protected(norm):
            return False
        if any(norm.startswith(p) for p in self.prefixes):
            return True
        return "/" not in norm and norm.lower().endswith(self.root_suffixes)


DEFAULT_WRITE_SCOPE = WriteScope()


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


def assert_writable(rel: str, *, advanced: bool = False, scope: WriteScope | None = None) -> str:
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
    if not (scope or DEFAULT_WRITE_SCOPE).allows(norm):
        raise ProtectedPathError(f"write not allowed: {norm}")
    return norm
