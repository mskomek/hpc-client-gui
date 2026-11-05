"""Byte-preserving save helpers (W65 SFTP-014 / SAFE-016)."""

from __future__ import annotations

import hashlib


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def byte_identity_ok(original: bytes, saved: bytes) -> bool:
    return sha256_bytes(original) == sha256_bytes(saved)


def single_token_patch(original: bytes, old_token: bytes, new_token: bytes) -> bytes:
    """Replace exactly one occurrence of ``old_token``.

    Raises ``ValueError`` when the token is absent or ambiguous, so callers
    can never silently rewrite the wrong span. Encoding/BOM/CRLF bytes
    outside the patched span are preserved verbatim.
    """
    if not old_token:
        raise ValueError("old_token must be non-empty")
    count = original.count(old_token)
    if count == 0:
        raise ValueError("token not found")
    if count != 1:
        raise ValueError(f"token is ambiguous: {count} occurrences")
    return original.replace(old_token, new_token, 1)
