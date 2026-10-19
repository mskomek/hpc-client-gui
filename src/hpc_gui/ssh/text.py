"""Text decoding helpers for SSH banners and command output."""

from __future__ import annotations


def decode_remote_text(data: bytes) -> str:
    """Decode remote text as UTF-8 while preserving readable replacement chars."""
    return data.decode("utf-8", errors="replace")
