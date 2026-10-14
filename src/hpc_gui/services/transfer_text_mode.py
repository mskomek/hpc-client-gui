"""Transfer mode detection and bounded text line-ending conversion."""

from __future__ import annotations

import os
from pathlib import Path

AUTO = "auto"
BINARY = "binary"
ASCII = "ascii"
TRANSFER_MODES = (AUTO, BINARY, ASCII)

# Bounded read size for classification samples and streaming conversion.
CHUNK_SIZE = 8192

_ASCII_INVALID = (
    "ASCII transfer requires UTF-8 text content; use Binary mode for this file."
)

TEXT_EXTENSIONS = {
    ".bash",
    ".cfg",
    ".conf",
    ".csv",
    ".ini",
    ".json",
    ".log",
    ".md",
    ".out",
    ".py",
    ".sbatch",
    ".sh",
    ".slurm",
    ".text",
    ".toml",
    ".tsv",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}


def normalize_transfer_mode(value: str, default: str = AUTO) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in TRANSFER_MODES else default


def looks_binary(data: bytes) -> bool:
    if b"\x00" in data:
        return True
    if not data:
        return False
    try:
        data[:8192].decode("utf-8")
    except UnicodeDecodeError:
        return True
    sample = data[:8192]
    suspicious = sum(1 for byte in sample if byte < 9 or (13 < byte < 32))
    return suspicious / len(sample) > 0.10


def is_known_text_path(path: str) -> bool:
    name = Path(path).name
    if not Path(name).suffix:
        return False
    return any(name.casefold().endswith(ext) for ext in TEXT_EXTENSIONS)


def resolve_transfer_mode(
    path: str, requested: str, sample: bytes | None = None
) -> str:
    requested = normalize_transfer_mode(requested)
    if requested == BINARY:
        return BINARY
    if sample is not None and looks_binary(sample):
        if requested == ASCII:
            raise ValueError(
                "ASCII transfer rejected because binary content was detected."
            )
        return BINARY
    if requested == ASCII:
        return ASCII
    return ASCII if is_known_text_path(path) else BINARY


def _ascii_bytes_for_remote(data: bytes) -> bytes:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(_ASCII_INVALID) from exc
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _ascii_bytes_for_local(data: bytes) -> bytes:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(_ASCII_INVALID) from exc
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.replace("\n", os.linesep).encode("utf-8")


def _is_utf8_prefix(tail: bytes) -> bool:
    """Whether ``tail`` starts a UTF-8 code point truncated at its end."""
    if not tail:
        return False
    lead = tail[0]
    if lead & 0x80 == 0:
        return True
    if lead & 0xE0 == 0xC0:
        needed = 1
    elif lead & 0xF0 == 0xE0:
        needed = 2
    elif lead & 0xF8 == 0xF0:
        needed = 3
    else:
        return False
    return len(tail) <= needed + 1 and all(
        byte & 0xC0 == 0x80 for byte in tail[1:]
    )


def _utf8_carry_split(data: bytes) -> tuple[str, bytes]:
    """Decode UTF-8 while carrying an incomplete trailing code point."""
    try:
        return data.decode("utf-8"), b""
    except UnicodeDecodeError as exc:
        tail = data[exc.start:]
        if not _is_utf8_prefix(tail) or exc.end != len(data):
            raise ValueError(_ASCII_INVALID) from None
        return data[: exc.start].decode("utf-8"), tail


def _flush_normalized_lines(
    text: str, newline: str, pending_cr: bool
) -> tuple[str, bool]:
    """Normalize CRLF/CR/LF while carrying a trailing CR across chunks."""
    parts: list[str] = []
    if pending_cr:
        if text.startswith("\n"):
            parts.append(newline)
            text = text[1:]
        else:
            parts.append(newline)
        pending_cr = False
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char == "\r":
            if index + 1 < length:
                if text[index + 1] == "\n":
                    parts.append(newline)
                    index += 2
                else:
                    parts.append(newline)
                    index += 1
            else:
                pending_cr = True
                index += 1
        elif char == "\n":
            parts.append(newline)
            index += 1
        else:
            parts.append(char)
            index += 1
    return "".join(parts), pending_cr


def _stream_utf8_lines(source_path: str, dest_path: str, newline: str) -> None:
    """Stream UTF-8 while normalizing line endings with bounded memory."""
    carry = b""
    pending_cr = False
    with open(source_path, "rb") as source, open(
        dest_path, "w", encoding="utf-8", newline=""
    ) as dest:
        while True:
            chunk = source.read(CHUNK_SIZE)
            if not chunk:
                break
            text, carry = _utf8_carry_split(carry + chunk)
            flushed, pending_cr = _flush_normalized_lines(text, newline, pending_cr)
            dest.write(flushed)
        if carry:
            raise ValueError(_ASCII_INVALID)
        if pending_cr:
            dest.write(newline)
