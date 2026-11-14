"""Bounded editor input checks and newline-preserving local writes."""

from __future__ import annotations

import codecs
import os


BINARY_GUARD_SIZE_BYTES = 2 * 1024 * 1024


def editor_binary_guard_reason(path: str, content: str) -> str | None:
    """Return a refusal reason for binary/oversized text-editor input."""
    try:
        text = content or ""
        if "\x00" in text:
            return f"Binary file not opened as text: {path or 'untitled'}"
        if len(text.encode("utf-8", "ignore")) > BINARY_GUARD_SIZE_BYTES:
            return f"File too large to edit safely (>2 MiB): {path or 'untitled'}"
    except Exception:
        return None
    return None


def write_local_text(path: str, content: str, encoding: str) -> None:
    """Write without newline conversion and validate the codec before truncation."""
    codecs.lookup(encoding)
    with open(path, "w", encoding=encoding, newline="") as handle:
        handle.write(content)


def disk_baseline(path: str):
    """Return the local file's (mtime_ns, size) or None when unavailable."""
    if not path:
        return None
    try:
        stat = os.stat(path)
        return (stat.st_mtime_ns, stat.st_size)
    except OSError:
        return None
