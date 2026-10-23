"""Framework-neutral data structures for source-preserving journal edits."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


BlockKind = Literal["tui-command", "scheme-expression", "comment", "raw"]


@dataclass(frozen=True, slots=True)
class JournalBlock:
    kind: BlockKind
    start: int
    end: int
    line: int
    column: int
    command_path: str | None = None
    verification_status: str = "unverified"
    diagnostic: str | None = None


@dataclass(frozen=True, slots=True)
class JournalDiagnostic:
    code: str
    message: str
    line: int
    column: int
    severity: Literal["info", "warning", "error"] = "warning"
    confidence: str = "structural"
    rule_id: str | None = None
    source_url: str | None = None


@dataclass(frozen=True, slots=True)
class ParsedJournal:
    source: str
    blocks: tuple[JournalBlock, ...]
    diagnostics: tuple[JournalDiagnostic, ...]

    def text_for(self, block: JournalBlock) -> str:
        return self.source[block.start : block.end]

    def replace(self, start: int, end: int, replacement: str) -> str:
        if start < 0 or end < start or end > len(self.source):
            raise ValueError("source span is outside the journal")
        return self.source[:start] + replacement + self.source[end:]

    def reorder(self, order: tuple[int, ...]) -> str:
        """Return an explicit whole-block reorder, preserving each block byte-for-byte."""
        if len(order) != len(self.blocks) or set(order) != set(range(len(self.blocks))):
            raise ValueError("order must contain each source block index exactly once")
        return "".join(self.text_for(self.blocks[index]) for index in order)
