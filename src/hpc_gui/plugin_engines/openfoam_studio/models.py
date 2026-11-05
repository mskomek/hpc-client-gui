"""Case documents retain original bytes until a concrete token is edited."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import hashlib

from hpc_gui.openfoam_core import DecodedSource, ParsedDictionary, parse_dictionary


@dataclass(slots=True)
class CaseDocument:
    relative_path: str
    path: str
    remote: bool
    original: bytes
    decoded: DecodedSource
    text: str
    expected_sha256: str
    read_only: bool = False
    modified: bool = False
    undo_stack: list[str] = field(default_factory=list, repr=False)
    redo_stack: list[str] = field(default_factory=list, repr=False)

    @classmethod
    def from_bytes(cls, relative_path: str, path: str, data: bytes, *, remote: bool = False, read_only: bool = False):
        decoded = DecodedSource.from_bytes(data)
        return cls(relative_path, path, remote, bytes(data), decoded, decoded.text, decoded.sha256, read_only=read_only)

    @property
    def parsed(self) -> ParsedDictionary:
        return parse_dictionary(self.text, path=self.path)

    def set_text(self, value: str) -> None:
        """Record one visual or source edit in bounded, per-document history."""
        if value == self.text:
            return
        if self.read_only:
            raise PermissionError("read-only case snapshot cannot be edited")
        self.undo_stack.append(self.text)
        if len(self.undo_stack) > 64 or sum(map(len, self.undo_stack)) > 2_000_000:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self.text = value
        self.modified = self.text != self.decoded.text

    def undo(self) -> bool:
        if self.read_only or not self.undo_stack:
            return False
        self.redo_stack.append(self.text)
        if len(self.redo_stack) > 64 or sum(map(len, self.redo_stack)) > 2_000_000:
            self.redo_stack.pop(0)
        self.text = self.undo_stack.pop()
        self.modified = self.text != self.decoded.text
        return True

    def redo(self) -> bool:
        if self.read_only or not self.redo_stack:
            return False
        self.undo_stack.append(self.text)
        if len(self.undo_stack) > 64 or sum(map(len, self.undo_stack)) > 2_000_000:
            self.undo_stack.pop(0)
        self.text = self.redo_stack.pop()
        self.modified = self.text != self.decoded.text
        return True

    def replace_scalar(self, key: str, value: str, *, scope: tuple[str, ...] = ()) -> None:
        self.set_text(self.parsed.replace_scalar(key, value, scope=scope))

    def to_bytes(self) -> bytes:
        return self.decoded.encode(self.text)

    def mark_saved(self, payload: bytes) -> None:
        self.original = bytes(payload)
        self.decoded = DecodedSource.from_bytes(payload)
        self.text = self.decoded.text
        self.expected_sha256 = hashlib.sha256(payload).hexdigest()
        self.modified = False


@dataclass(frozen=True, slots=True)
class SaveReport:
    success: bool
    partial: bool
    saved: tuple[str, ...]
    conflicts: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    recovery_paths: tuple[str, ...] = ()


class SaveConflictError(RuntimeError):
    pass


def dictionary_bytes(path: str | Path, *, maximum: int) -> bytes:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise OSError("refusing to open a symlink or non-file")
    if target.stat().st_size > maximum:
        raise ValueError("dictionary exceeds the configured size limit")
    return target.read_bytes()


@dataclass(frozen=True, slots=True)
class CaseSearchHit:
    relative_path: str
    line: int
    column: int
    text: str
