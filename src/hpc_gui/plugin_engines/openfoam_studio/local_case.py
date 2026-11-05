"""Bounded local case loading; large results and symlinks remain metadata-only."""
from __future__ import annotations

from pathlib import Path, PurePosixPath

from hpc_gui.openfoam_core import discover_case_files, is_dictionary_name, safe_relative_path

from .models import CaseDocument, SaveReport, dictionary_bytes
from .safe_save import save_local_case


class LocalCase:
    def __init__(self, root: str | Path, *, read_only: bool = False):
        self.root = Path(root).resolve(strict=True)
        self.read_only = bool(read_only)
        if not self.root.is_dir():
            raise ValueError("selected case root is not a directory")
        self.documents: dict[str, CaseDocument] = {}
        self.refresh()

    def refresh(self) -> tuple[str, ...]:
        files = discover_case_files(self.root)
        known = {item.relative_path for item in files}
        for relative in tuple(self.documents):
            if relative not in known and not self.documents[relative].modified:
                self.documents.pop(relative, None)
        for item in files:
            if item.relative_path not in self.documents:
                self.documents[item.relative_path] = CaseDocument.from_bytes(
                    item.relative_path, str(item.absolute_path), item.data, read_only=self.read_only
                )
        return tuple(sorted(known))

    def open_dictionary(self, path: str | Path) -> CaseDocument:
        candidate = Path(path)
        if not candidate.is_absolute():
            if not safe_relative_path(candidate.as_posix()):
                raise ValueError("selected case-relative path is unsafe")
            candidate = self.root / candidate
        if not safe_relative_path(candidate.relative_to(self.root).as_posix()):
            raise ValueError("selected case-relative path is unsafe")
        cursor = candidate
        while cursor != self.root:
            if cursor.is_symlink():
                raise ValueError("selected dictionary traverses a symbolic link")
            cursor = cursor.parent
        target = candidate.resolve(strict=True)
        if self.root not in target.parents or not is_dictionary_name(target.name):
            raise ValueError("selected file is outside the case or is not a dictionary")
        relative = target.relative_to(self.root).as_posix()
        document = self.documents.get(relative)
        if document is None:
            from hpc_gui.openfoam_core import MAX_DICTIONARY_BYTES
            data = dictionary_bytes(target, maximum=MAX_DICTIONARY_BYTES)
            document = CaseDocument.from_bytes(relative, str(target), data, read_only=self.read_only)
            self.documents[relative] = document
        return document

    def save(self):
        if self.read_only:
            return SaveReport(False, False, (), errors=("case workspace is a read-only snapshot",))
        report = save_local_case(self.root, self.documents)
        if report.success:
            self.refresh()
        return report

    def tree_paths(self) -> tuple[str, ...]:
        files = discover_case_files(self.root)
        directories: set[str] = set()
        leaves: list[str] = []
        for item in files:
            relative = PurePosixPath(item.relative_path)
            leaves.append(relative.as_posix())
            for parent in relative.parents:
                if parent.as_posix() != ".":
                    directories.add(parent.as_posix() + "/")
        return tuple(sorted(directories, key=lambda value: (value.count("/"), value)) + sorted(leaves))
