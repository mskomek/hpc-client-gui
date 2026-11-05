"""Host-facing case workspace facade shared by the Case Studio page."""
from __future__ import annotations

from pathlib import Path, PurePosixPath
import re

from hpc_gui.openfoam_core import is_dictionary_name, parse_region_properties, safe_relative_path

from .local_case import LocalCase
from .models import CaseSearchHit, SaveReport
from .remote_case import recover_remote_case, save_remote_case, scan_remote_case
from .run_script_store import create_local_allrun, create_remote_allrun


class CaseWorkspace:
    def __init__(self, root: str, *, remote: bool = False, files=None, read_only: bool = False):
        self.root = str(root)
        self.remote = bool(remote)
        self.read_only = bool(read_only)
        self.files = files
        if self.remote:
            if files is None:
                raise RuntimeError("remote file service is unavailable")
            self.case = None
            self.documents = scan_remote_case(self.root, files, read_only=self.read_only)
        else:
            self.case = LocalCase(Path(root), read_only=self.read_only)
            self.documents = self.case.documents
        self._refresh_paths()

    def _refresh_paths(self):
        if self.remote:
            directories: set[str] = set()
            leaves = []
            for relative in self.documents:
                parts = PurePosixPath(relative)
                leaves.append(parts.as_posix())
                for parent in parts.parents:
                    if parent.as_posix() != ".":
                        directories.add(parent.as_posix() + "/")
            self.paths = tuple(sorted(directories, key=lambda value: (value.count("/"), value)) + sorted(leaves))
        else:
            self.paths = self.case.tree_paths()

    def open_dictionary(self, path: str):
        if self.remote:
            target = PurePosixPath(path)
            root = PurePosixPath(self.root)
            if not target.is_absolute():
                if not safe_relative_path(str(target)):
                    raise ValueError("unsafe remote case-relative path")
                target = root / target
            if not target.is_absolute():
                raise ValueError("remote dictionary path must be absolute")
            relative = target.relative_to(root).as_posix() if root in target.parents else ""
            if not safe_relative_path(relative) or not is_dictionary_name(target.name):
                raise ValueError("selected remote path is outside the case or is not a dictionary")
            document = self.documents.get(relative)
            if document is None:
                raise ValueError("selected remote dictionary was outside the bounded case scan")
            return document
        return self.case.open_dictionary(path)

    @property
    def region_properties(self):
        """Return static region metadata when the case declares it."""
        document = self.documents.get("constant/regionProperties")
        return None if document is None else parse_region_properties(document.parsed)

    def save(self):
        if self.read_only:
            return SaveReport(False, False, (), errors=("case workspace is a read-only snapshot",))
        if self.remote:
            return save_remote_case(self.root, self.files, self.documents)
        return self.case.save()

    def recover_save(self, recovery_paths):
        """Restore or clean a prior remote save after reconnecting."""
        if self.read_only:
            return SaveReport(False, False, (), errors=("case workspace is a read-only snapshot",))
        if not self.remote or self.files is None:
            return SaveReport(False, False, (), errors=("remote case recovery is unavailable",))
        return recover_remote_case(self.root, self.files, recovery_paths, self.documents)

    def create_allrun(self, content: str) -> str:
        """Create a case-local Allrun without replacing an existing file."""
        if self.read_only:
            raise PermissionError("case workspace is a read-only snapshot")
        if self.remote:
            return create_remote_allrun(self.root, self.files, content)
        return create_local_allrun(self.root, content)


    def search(self, query: str, *, case_sensitive: bool = False, limit: int = 500) -> tuple[CaseSearchHit, ...]:
        """Search the bounded dictionary snapshot, including unsaved edits."""
        needle = str(query).strip()
        maximum = min(int(limit), 500)
        if not needle or maximum <= 0:
            return ()
        pattern = re.compile(re.escape(needle), 0 if case_sensitive else re.IGNORECASE)
        hits: list[CaseSearchHit] = []
        for relative in sorted(self.documents):
            document = self.documents[relative]
            for line_number, line in enumerate(document.text.splitlines(), start=1):
                for match in pattern.finditer(line):
                    hits.append(CaseSearchHit(relative, line_number, match.start() + 1, line))
                    if len(hits) >= maximum:
                        return tuple(hits)
        return tuple(hits)

    def modified_paths(self) -> tuple[str, ...]:
        return tuple(sorted(name for name, document in self.documents.items() if document.modified))
