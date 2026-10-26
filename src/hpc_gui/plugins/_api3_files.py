"""No-follow file helpers for the Plugin API v3 host pin gate.

Cohesive boundary: safe package-relative POSIX path validation, link /
reparse-point rejection, and hash-verified reads that never follow links.
The policy gate itself lives in ``plugins.trusted_api3`` and re-exports
the helpers it needs so existing imports keep working.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

API3_DECLARATIVE_SUFFIXES = frozenset({".json", ".md", ".txt", ".tpl"})
API3_LINTER_ENGINE_SUFFIX = ".py"


def api3_pin_path_error(path: Any, role: Any) -> str | None:
    """Validate one host pin path before any filesystem access.

    Rejects absolute paths, drive prefixes, backslashes, NUL/control
    characters, empty/dot/dotdot segments, percent-encoded traversal, and
    URL schemes. Enforces narrow suffix/role combinations: only the
    ``linter-engine`` or ``application-engine`` role may use ``.py``;
    ``application-catalog`` is restricted to JSON; every other role must use
    a declarative suffix. Callers must fail closed on any non-None return.
    """
    if not isinstance(path, str) or not path:
        return "pinned payload path must be a non-empty string"
    if "\\" in path or "\x00" in path:
        return f"pinned payload path is unsafe: {path!r}"
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in path):
        return f"pinned payload path carries control characters: {path!r}"
    if path.startswith("/"):
        return f"pinned payload path must be package-relative: {path!r}"
    if len(path) >= 2 and path[1] == ":":
        return f"pinned payload path must not carry a drive prefix: {path!r}"
    lowered = path.lower()
    if "://" in lowered:
        return f"pinned payload path must not be a URL: {path!r}"
    if "%" in path:
        return f"pinned payload path must not be percent-encoded: {path!r}"
    segments = path.split("/")
    if any(segment in ("", ".", "..") for segment in segments):
        return f"pinned payload path must not escape the package: {path!r}"
    leaf = segments[-1]
    suffix = "." + leaf.rsplit(".", 1)[-1].lower() if "." in leaf else ""
    if role == "application-catalog":
        if suffix != ".json":
            return f"pinned application catalog needs a .json suffix: {path!r}"
    elif role in {"linter-engine", "application-engine"}:
        if suffix != API3_LINTER_ENGINE_SUFFIX:
            return f"pinned linter-engine payload needs a .py suffix: {path!r}"
    elif suffix not in API3_DECLARATIVE_SUFFIXES:
        return f"pinned payload {path!r} has a forbidden suffix {suffix!r} for role {role!r}"
    return None


def is_api3_link(path: Path) -> bool:
    """True for symlinks and (where exposed) junctions/reparse points."""
    try:
        if path.is_symlink():
            return True
    except OSError:
        return False
    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction):
        try:
            if is_junction():
                return True
        except OSError:
            return False
    return False


def api3_components_have_links(base: Path, rel: str) -> bool:
    """Reject links on every path component from base through rel."""
    current = base
    for segment in rel.split("/"):
        current = current / segment
        if is_api3_link(current):
            return True
    return False


def _hash_fd(fd: int) -> str:
    digest = hashlib.sha256()
    while True:
        chunk = os.read(fd, 65536)
        if not chunk:
            break
        digest.update(chunk)
    return digest.hexdigest()


def sha_of_nofollow(path: Path) -> str:
    """SHA-256 of one file without following links (fail closed on links)."""
    if is_api3_link(path):
        raise OSError(f"refusing to hash a link: {path}")
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    if nofollow and os.name == "posix":
        fd = os.open(path, os.O_RDONLY | nofollow)
        try:
            return _hash_fd(fd)
        finally:
            os.close(fd)
    with path.open("rb") as handle:
        digest = hashlib.sha256()
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_verified_bytes(package_dir: Path, rel: str, expected_sha: str) -> bytes:
    """Read one pinned payload without following links; verify its hash.

    Raises ``OSError`` (fail closed) when the path is a link, escapes the
    package, or its bytes do not match ``expected_sha``. Uses ``O_NOFOLLOW``
    where the OS supports it.
    """
    base = Path(package_dir)
    if is_api3_link(base):
        raise OSError("plugin package directory is a link")
    if api3_components_have_links(base, rel):
        raise OSError(f"pinned payload is a link: {rel}")
    target = base / rel
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    if nofollow and os.name == "posix":
        fd = os.open(target, os.O_RDONLY | nofollow)
        try:
            chunks: list[bytes] = []
            while True:
                chunk = os.read(fd, 65536)
                if not chunk:
                    break
                chunks.append(chunk)
            data = b"".join(chunks)
        finally:
            os.close(fd)
    else:
        if is_api3_link(target):
            raise OSError(f"pinned payload is a link: {rel}")
        data = target.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha:
        raise OSError(f"payload integrity mismatch for {rel!r}")
    return data
