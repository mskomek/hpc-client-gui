"""Strict UTF-8 decoding with byte-preserving round-trips (W65 LINT-COMPAT).

Never executes content. Invalid byte sequences raise ``UnicodeError`` so
callers can diagnose them without modifying the source.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DecodedSource:
    """Decoded dictionary bytes with their original framing preserved."""

    text: str
    sha256: str
    newline: str = "\n"
    had_bom: bool = False

    @classmethod
    def from_bytes(cls, data: bytes) -> "DecodedSource":
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("dictionary payload must be bytes")
        raw = bytes(data)
        had_bom = raw.startswith(b"\xef\xbb\xbf")
        body = raw[3:] if had_bom else raw
        text = body.decode("utf-8", errors="strict")
        if "\x00" in text:
            raise UnicodeError("dictionary bytes contain NUL")
        if "\r\n" in text:
            newline = "\r\n"
        elif "\r" in text:
            newline = "\r"
        else:
            newline = "\n"
        return cls(
            text=text,
            sha256=hashlib.sha256(raw).hexdigest(),
            newline=newline,
            had_bom=had_bom,
        )

    def encode(self, text: str) -> bytes:
        """Re-apply the original BOM/newline framing to edited text."""
        if not isinstance(text, str):
            raise TypeError("dictionary text must be str")
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        framed = normalized.replace("\n", self.newline)
        payload = framed.encode("utf-8", errors="strict")
        return (b"\xef\xbb\xbf" + payload) if self.had_bom else payload


def preferred_newline(text: str) -> str:
    """Newline style already used by ``text`` (defaults to ``\\n``)."""
    if not isinstance(text, str):
        raise TypeError("dictionary text must be str")
    if "\r\n" in text:
        return "\r\n"
    if "\r" in text:
        return "\r"
    return "\n"
