"""Framework-neutral editor document and command models."""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class DocumentModel:
    path: str = ""
    content: str = ""
    saved_content: str = ""
    is_local: bool = False
    encoding: str = "utf-8"
    suggested_filename: str = ""

    @property
    def dirty(self) -> bool:
        return self.content != self.saved_content

    def with_content(self, content: str) -> "DocumentModel":
        return replace(self, content=content)

    def mark_saved(self, content: str | None = None) -> "DocumentModel":
        value = self.content if content is None else content
        return replace(self, content=value, saved_content=value)


@dataclass(frozen=True)
class LintResult:
    line: int
    column: int
    message: str
    severity: str = "warning"


class EditorController:
    def __init__(self) -> None:
        self.documents: list[DocumentModel] = []
        self.active_index = -1

    def open(self, document: DocumentModel) -> int:
        for index, current in enumerate(self.documents):
            if document.path and current.path == document.path:
                self.active_index = index
                return index
        self.documents.append(document)
        self.active_index = len(self.documents) - 1
        return self.active_index

    @property
    def active(self) -> DocumentModel | None:
        return self.documents[self.active_index] if 0 <= self.active_index < len(self.documents) else None

    def update_content(self, content: str) -> DocumentModel:
        if self.active is None:
            raise RuntimeError("no active document")
        self.documents[self.active_index] = self.active.with_content(content)
        return self.documents[self.active_index]

    def mark_saved(self, content: str | None = None) -> DocumentModel:
        if self.active is None:
            raise RuntimeError("no active document")
        self.documents[self.active_index] = self.active.mark_saved(content)
        return self.documents[self.active_index]


class EditorCommandService:
    @staticmethod
    def execute_mode(path: str, *, force_submit: bool = False, run_in_terminal: bool = False) -> str:
        lower = (path or "").lower()
        if force_submit or lower.endswith((".slurm", ".sbatch")):
            return "submit"
        if run_in_terminal or lower.endswith(".sh"):
            return "run"
        return "save"

    @staticmethod
    def suggested_filename(path: str, fallback: str = "untitled.sh") -> str:
        return path.rstrip("/\\").rsplit("/", 1)[-1].rsplit("\\", 1)[-1] or fallback

