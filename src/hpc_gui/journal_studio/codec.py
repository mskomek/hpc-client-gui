"""Journal byte decoding with an exact no-edit round trip."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re


MAX_JOURNAL_BYTES = 128 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class DecodedJournal:
    text: str
    encoding: str
    bom: bytes
    original_bytes: bytes
    original_sha256: str
    decode_warning: str | None = None

    def encode(self, text: str) -> bytes:
        if text == self.text:
            return self.original_bytes
        try:
            return self.bom + text.encode(self.encoding, errors="strict")
        except UnicodeEncodeError as exc:
            raise ValueError(
                f"Edited text cannot be represented using the original {self.encoding} encoding"
            ) from exc

    @property
    def newline_counts(self) -> dict[str, int]:
        return {
            "crlf": self.text.count("\r\n"),
            "lf": len(re.findall(r"(?<!\r)\n", self.text)),
            "cr": len(re.findall(r"\r(?!\n)", self.text)),
        }

    @property
    def preferred_newline(self) -> str:
        counts = self.newline_counts
        return max((("\r\n", counts["crlf"]), ("\n", counts["lf"]), ("\r", counts["cr"])), key=lambda item: item[1])[0]


def decode_journal(data: bytes, *, name: str = "journal") -> DecodedJournal:
    if len(data) > MAX_JOURNAL_BYTES:
        raise ValueError(f"{name} exceeds the {MAX_JOURNAL_BYTES // (1024 * 1024)} MiB edit limit")

    encoding = "utf-8"
    bom = b""
    warning = None
    payload = data
    if data.startswith(b"\x00\x00\xfe\xff"):
        encoding, bom, payload = "utf-32-be", data[:4], data[4:]
    elif data.startswith(b"\xff\xfe\x00\x00"):
        encoding, bom, payload = "utf-32-le", data[:4], data[4:]
    elif data.startswith(b"\xef\xbb\xbf"):
        bom, payload = data[:3], data[3:]
    elif data.startswith(b"\xfe\xff"):
        encoding, bom, payload = "utf-16-be", data[:2], data[2:]
    elif data.startswith(b"\xff\xfe"):
        encoding, bom, payload = "utf-16-le", data[:2], data[2:]

    try:
        text = payload.decode(encoding, errors="strict")
    except UnicodeDecodeError:
        if bom:
            raise ValueError(f"{name} has an invalid {encoding} byte sequence")
        encoding = "cp1252"
        warning = "Source is not valid UTF-8; Windows-1252 was selected to preserve its bytes."
        try:
            text = payload.decode(encoding, errors="strict")
        except UnicodeDecodeError:
            # shortcut: cp1252 leaves 5 byte values undefined; latin-1 maps every byte, so the source still round-trips.
            encoding = "latin-1"
            warning = "Source is not valid UTF-8 or Windows-1252; Latin-1 was selected to preserve its bytes."
            text = payload.decode(encoding)

    return DecodedJournal(
        text=text,
        encoding=encoding,
        bom=bom,
        original_bytes=bytes(data),
        original_sha256=hashlib.sha256(data).hexdigest(),
        decode_warning=warning,
    )
