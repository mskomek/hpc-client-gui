"""Binary/size guard leaf for the wx editor."""

from __future__ import annotations

import codecs
import os


BINARY_GUARD_SIZE_BYTES = 2 * 1024 * 1024


def editor_binary_guard_reason(path: str, content: str) -> str | None:
    """Return a human-readable refusal reason, or ``None`` when editable."""
    try:
        text = content or ""
        if "\x00" in text:
            return f"Binary file not opened as text: {path or 'untitled'}"
        if len(text.encode("utf-8", "ignore")) > BINARY_GUARD_SIZE_BYTES:
            return f"File too large to edit safely (>2 MiB): {path or 'untitled'}"
    except Exception:
        return None
    return None


def _write_local_text(path: str, content: str, encoding: str) -> None:
    """Write editor content to a local path without host newline translation.

    The codec is looked up before the file is opened so an unknown encoding
    fails without truncating the existing file (HPC-W06-EDIT-021).
    """
    codecs.lookup(encoding)
    with open(path, "w", encoding=encoding, newline="") as handle:
        handle.write(content)


def _disk_baseline(path: str):
    """``(mtime_ns, size)`` snapshot of a local path, or ``None``."""
    try:
        if not path:
            return None
        st = os.stat(path)
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return None


__all__ = [
    "BINARY_GUARD_SIZE_BYTES",
    "_disk_baseline",
    "_write_local_text",
    "editor_binary_guard_reason",
]
