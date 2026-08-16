from __future__ import annotations

import os
import inspect
import json
import tempfile
from pathlib import Path


AUTO = "auto"
BINARY = "binary"
ASCII = "ascii"
TRANSFER_MODES = (AUTO, BINARY, ASCII)

# Bounded read size for classification samples and streaming conversion.
CHUNK_SIZE = 8192

# Suffix for an in-progress transfer. The planner reads it too, so that a
# leftover chunk from a cancelled download is offered to the user instead of
# being resumed or discarded behind their back.
PARTIAL_SUFFIX = ".part"

_ASCII_INVALID = (
    "ASCII transfer requires UTF-8 text content; use Binary mode for this file."
)

# ``.dat`` stays out of the known-text set on purpose: in Auto mode data
# files are transferred as Binary unless the user explicitly picks ASCII.
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
    suspicious = sum(
        1 for byte in sample if byte < 9 or (13 < byte < 32)
    )
    return suspicious / len(sample) > 0.10


def is_known_text_path(path: str) -> bool:
    name = Path(path).name
    if not Path(name).suffix:
        return False
    return any(name.casefold().endswith(ext) for ext in TEXT_EXTENSIONS)


def resolve_transfer_mode(path: str, requested: str, sample: bytes | None = None) -> str:
    requested = normalize_transfer_mode(requested)
    if requested == BINARY:
        return BINARY
    if sample is not None and looks_binary(sample):
        if requested == ASCII:
            raise ValueError("ASCII transfer rejected because binary content was detected.")
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
    """Return True when ``tail`` is the (possibly truncated) start of a
    UTF-8 code point, i.e. safe to carry into the next read chunk."""
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
    """Decode ``data`` as UTF-8, returning ``(text, carry)`` where ``carry``
    holds an incomplete trailing code point to join with the next chunk.

    Raises ``ValueError`` when ``data`` is not valid UTF-8 text, matching the
    whole-file conversion helpers.
    """
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
    """Normalize every CRLF/CR/LF in ``text`` to ``newline``.

    A trailing CR is held back across chunk boundaries so a CRLF split by a
    read boundary still collapses into a single newline.
    """
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
    """Stream ``source_path`` as UTF-8 into ``dest_path``, normalizing every
    line terminator (CRLF/CR/LF) to ``newline``.

    Reads bounded chunks and never loads the whole file for conversion, so
    ASCII conversion stays O(chunk) in memory for arbitrarily large files.
    """
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
            # A file that ends inside a multi-byte sequence is not valid UTF-8.
            raise ValueError(_ASCII_INVALID)
        if pending_cr:
            dest.write(newline)


def _upload_remote(files, local_path: str, remote_path: str, progress_cb=None, resume_identity=None) -> None:
    """Upload to a server-side ``<remote>.part`` and rename once when the
    backend can rename; otherwise upload directly to the final name.

    The ``.part`` name keeps a partially uploaded file from shadowing the
    destination and still lets rename-capable backends resume against the
    same server-side partial on a retry.
    """
    rename = getattr(files, "rename", None)
    if not callable(rename):
        _upload_file(files, local_path, remote_path, progress_cb=progress_cb)
        return
    temp_remote = remote_path + PARTIAL_SUFFIX
    meta_remote = temp_remote + ".meta"
    source = Path(local_path).stat()
    identity = json.dumps(resume_identity or {"path": str(remote_path), "size": source.st_size, "mtime_ns": source.st_mtime_ns}, sort_keys=True)
    try:
        if files.exists(temp_remote):
            try:
                if files.read_text(meta_remote) != identity:
                    files.remove(temp_remote)
            except Exception:
                files.remove(temp_remote)
        files.write_text(meta_remote, identity)
    except (AttributeError, NotImplementedError):
        pass
    _upload_file(files, local_path, temp_remote, progress_cb=progress_cb)
    rename(temp_remote, remote_path)
    try:
        files.remove(meta_remote)
    except (AttributeError, FileNotFoundError, NotImplementedError):
        pass


def _upload_file(files, local_path: str, remote_path: str, progress_cb=None) -> None:
    try:
        signature = inspect.signature(files.upload)
        if "progress_cb" in signature.parameters:
            files.upload(local_path, remote_path, progress_cb=progress_cb)
            return
    except (TypeError, ValueError):
        pass
    files.upload(local_path, remote_path)


def upload_with_mode(
    files,
    local_path: str,
    remote_path: str,
    requested: str,
    progress_cb=None,
) -> str:
    with open(local_path, "rb") as source:
        sample = source.read(CHUNK_SIZE)
    effective = resolve_transfer_mode(local_path, requested, sample)
    source_stat = Path(local_path).stat()
    resume_identity = {"path": str(remote_path), "size": source_stat.st_size, "mtime_ns": source_stat.st_mtime_ns}
    if effective == BINARY:
        _upload_remote(files, local_path, remote_path, progress_cb=progress_cb, resume_identity=resume_identity)
        return effective
    # ASCII conversion streams the source so its line endings can be
    # normalized before the backend upload without ever materializing the
    # whole file in memory.
    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp_path = temp.name
        _stream_utf8_lines(local_path, temp_path, "\n")
        _upload_remote(files, temp_path, remote_path, progress_cb=progress_cb, resume_identity=resume_identity)
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
    return effective


def _download_file(files, remote_path: str, local_path: str, progress_cb=None) -> None:
    try:
        signature = inspect.signature(files.download)
        if "progress_cb" in signature.parameters:
            files.download(remote_path, local_path, progress_cb=progress_cb)
            return
    except (TypeError, ValueError):
        pass
    files.download(remote_path, local_path)


def download_with_mode(
    files,
    remote_path: str,
    local_path: str,
    requested: str,
    progress_cb=None,
) -> str:
    destination = Path(local_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    part_path = Path(str(destination) + PARTIAL_SUFFIX)
    meta_path = Path(str(part_path) + ".meta")
    remote_stat = getattr(files, "stat", None)
    if callable(remote_stat):
        remote_size, remote_mtime = remote_stat(remote_path)
        identity = {"path": str(remote_path), "size": remote_size, "mtime": remote_mtime}
        try:
            saved = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            saved = None
        if part_path.exists() and saved != identity:
            part_path.unlink(missing_ok=True)
        meta_path.write_text(json.dumps(identity, sort_keys=True), encoding="utf-8")
    _download_file(files, remote_path, str(part_path), progress_cb=progress_cb)
    try:
        with open(part_path, "rb") as stream:
            sample = stream.read(CHUNK_SIZE)
    except OSError:
        sample = b""
    effective = resolve_transfer_mode(remote_path, requested, sample)
    if effective == ASCII:
        converted_path = Path(str(destination) + ".tmp")
        try:
            _stream_utf8_lines(str(part_path), str(converted_path), os.linesep)
            os.replace(converted_path, destination)
        finally:
            try:
                converted_path.unlink(missing_ok=True)
            except OSError:
                pass
        try:
            part_path.unlink(missing_ok=True)
        except OSError:
            pass
    else:
        os.replace(part_path, destination)
    meta_path.unlink(missing_ok=True)
    return effective
