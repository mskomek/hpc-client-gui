"""Framework-neutral editor document and command models."""

from __future__ import annotations

from dataclasses import dataclass, replace


def detect_newline(content: str) -> str:
    """Return the dominant newline style of *content* (``"\\r\\n"`` or ``"\\n"``).

    W26 (HPC-W06-EDIT-013) preserves the on-open newline style across saves
    instead of silently normalizing line endings.
    """
    try:
        text = content or ""
        if "\r\n" in text:
            # Dominant-style vote: CRLF wins ties so mixed content opened
            # from a Windows-authored file keeps CRLF.
            if text.count("\r\n") * 2 >= text.count("\n"):
                return "\r\n"
        return "\n"
    except Exception:
        return "\n"


def normalize_newlines_for_save(content: str, newline: str) -> str:
    """Render *content* with the document's pinned newline style."""
    try:
        text = content or ""
        # Collapse first (wx TextCtrl on Windows may surface lone or doubled
        # carriage returns), then render the pinned style exactly once.
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        if newline == "\r\n":
            return text.replace("\n", "\r\n")
        return text
    except Exception:
        return content


@dataclass(frozen=True)
class DocumentModel:
    path: str = ""
    content: str = ""
    saved_content: str = ""
    is_local: bool = False
    encoding: str = "utf-8"
    suggested_filename: str = ""
    # W26 document identity (HPC-W06-EDIT-010..016): remote documents pin the
    # connection they were opened from so a later connection/profile switch
    # cannot redirect Save to the wrong host/path (HPC-W06-EDIT-016).
    provider: str = ""
    profile: str = ""
    session_key: str = ""
    # W26 preservation metadata (HPC-W06-EDIT-013/015).
    newline: str = "\n"
    version: str = ""

    @property
    def dirty(self) -> bool:
        return self.content != self.saved_content

    @property
    def canonical_key(self) -> tuple:
        """Identity key distinguishing local vs remote, connection, and path."""
        norm_path = str(self.path or "").strip().replace("\\", "/")
        if self.is_local:
            return (True, "", "", "", norm_path.lower())
        return (
            False,
            str(self.provider or ""),
            str(self.profile or ""),
            str(self.session_key or ""),
            norm_path,
        )

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
        key = document.canonical_key
        for index, current in enumerate(self.documents):
            if current.canonical_key == key and key[4]:
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

