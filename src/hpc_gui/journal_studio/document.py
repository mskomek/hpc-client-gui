"""Editable journal document and conflict-aware local persistence."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
import tempfile

from hpc_gui.journal_studio.codec import DecodedJournal, decode_journal


class JournalConflictError(RuntimeError):
    """The file changed since it was opened or a new target already exists."""


@dataclass(slots=True)
class JournalDocument:
    text: str
    encoding: str = "utf-8"
    newline: str = "\n"
    bom: bytes = b""
    path: str | None = None
    remote: bool = False
    original_bytes: bytes = b""
    saved_text: str = ""
    expected_sha256: str | None = None
    decode_warning: str | None = None

    @classmethod
    def from_bytes(cls, data: bytes, *, path: str | None = None, remote: bool = False) -> "JournalDocument":
        decoded: DecodedJournal = decode_journal(data, name=path or "journal")
        return cls(
            text=decoded.text,
            encoding=decoded.encoding,
            newline=decoded.preferred_newline,
            bom=decoded.bom,
            path=path,
            remote=remote,
            original_bytes=decoded.original_bytes,
            saved_text=decoded.text,
            expected_sha256=decoded.original_sha256,
            decode_warning=decoded.decode_warning,
        )

    @classmethod
    def new(cls, *, path: str | None = None, remote: bool = False, text: str = "") -> "JournalDocument":
        return cls(text=text, path=path, remote=remote, saved_text="")

    @property
    def modified(self) -> bool:
        return self.text != self.saved_text

    def to_bytes(self) -> bytes:
        if not self.modified:
            return self.original_bytes
        try:
            return self.bom + self.text.encode(self.encoding, errors="strict")
        except UnicodeEncodeError as exc:
            raise ValueError(f"Text cannot be saved with the original {self.encoding} encoding") from exc

    def mark_saved(self, data: bytes, *, saved_text: str | None = None) -> None:
        self.original_bytes = bytes(data)
        self.saved_text = self.text if saved_text is None else saved_text
        self.expected_sha256 = hashlib.sha256(data).hexdigest()


def write_local_atomic(path: str | Path, data: bytes, *, expected_sha256: str | None) -> str:
    """Atomically write a local file after checking its open-time fingerprint."""
    target = Path(path)
    parent = target.parent
    if not parent.is_dir():
        raise OSError(f"Save directory does not exist: {parent}")
    if target.is_symlink():
        raise OSError("Refusing to save through a symbolic link")
    def verify_target() -> None:
        if target.is_symlink():
            raise OSError("Refusing to save through a symbolic link")
        exists_now = target.exists()
        if exists_now:
            current = hashlib.sha256(target.read_bytes()).hexdigest()
            if expected_sha256 is None or current != expected_sha256:
                raise JournalConflictError("The file changed after it was opened. Compare or reopen before saving.")
        elif expected_sha256 is not None:
            raise JournalConflictError("The file was removed after it was opened. Save As to keep your edits.")

    verify_target()
    original_mode = target.stat().st_mode if target.exists() else None
    if original_mode is not None and not os.access(target, os.W_OK):
        raise PermissionError(f"Journal is not writable: {target}")

    fd, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".journal-tmp", dir=parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if original_mode is not None:
            os.chmod(temporary_name, stat.S_IMODE(original_mode))
        verify_target()
        os.replace(temporary_name, target)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise
    return hashlib.sha256(data).hexdigest()
