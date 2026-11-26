"""Read-only, bounded local/remote file lint plans and grouped results.

No GUI imports. An explicit unsupported file, scan limit or read failure is
reported rather than interpreted as a clean lint result.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
import os
import stat

from hpc_gui.lint.engine import MAX_LINT_TEXT_BYTES, lint_text
from hpc_gui.lint.models import Severity
from hpc_gui.services.file_open import decode_text

MAX_FILES = 200
MAX_SCAN_ENTRIES = 10000
MAX_BATCH_BYTES = 50 * 1024 * 1024


class FileLintCancelled(RuntimeError):
    pass


@dataclass(frozen=True)
class Document:
    path: str
    text: str


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str
    line: int | None = None
    column: int | None = None
    explanation: str = ""
    suggested_fix: str = ""
    source_url: str = ""
    is_heuristic: bool = False


@dataclass(frozen=True)
class FileResult:
    file_path: str
    detection: object
    diagnostics: tuple[Finding, ...]

    @property
    def summary(self):
        return {s.value: sum(d.severity == s for d in self.diagnostics) for s in Severity}

    def sorted_diagnostics(self):
        return sorted(self.diagnostics, key=lambda d: (d.line or 0, d.column or 0, d.code))


@dataclass(frozen=True)
class RunResult:
    files: tuple[FileResult, ...]


@dataclass(frozen=True)
class LintCatalog:
    packs: tuple
    tools: tuple  # (tool, frozenset[suffix])

    def matching(self, path):
        suffix = PurePosixPath(path.replace("\\", "/")).suffix.lower()
        return ([p for p in self.packs if p.matches(path)],
                [tool for tool, suffixes in self.tools if suffix in suffixes])

    def common_tools(self, documents):
        if not documents:
            return ()
        return tuple(tool for tool, suffixes in self.tools
                     if all(PurePosixPath(d.path.replace("\\", "/")).suffix.lower() in suffixes
                            for d in documents))


def load_catalog():
    from hpc_gui.lint.rulepack import load_lint_packs
    from hpc_gui.plugins.linter_tools import list_linter_tools, tool_supported_suffixes

    return LintCatalog(tuple(load_lint_packs()),
                       tuple((tool, tool_supported_suffixes(tool)) for tool in list_linter_tools()))


def _check(current):
    if not current():
        raise FileLintCancelled("File lint selection is no longer current.")


def _kind(mode, directory):
    kind = stat.S_IFMT(int(mode or 0))
    if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
        raise ValueError("Symbolic links and special files are not supported for lint.")
    if kind and (kind == stat.S_IFDIR) != bool(directory):
        raise ValueError("File type changed during lint discovery.")
    return bool(directory)


def _remote_path(path):
    value = str(path)
    normalized = str(PurePosixPath(value))
    if not value.startswith("/") or normalized != value or ".." in PurePosixPath(value).parts:
        raise ValueError(f"Unsafe remote lint path: {value!r}")
    return value


def _local_root(path, expected_dir):
    p = Path(path).absolute()
    info = p.lstat()
    _kind(info.st_mode, expected_dir)
    if any(parent.is_symlink() for parent in p.parents):
        raise ValueError(f"Symbolic-link ancestor: {p}")
    return str(p)


def _remote_root(files, path, expected_dir):
    path = _remote_path(path)
    lstat = getattr(files, "lstat_entry", None)
    if callable(lstat):
        entry = lstat(path)
        if bool(entry.is_dir) != bool(expected_dir):
            raise ValueError(f"File type changed: {path}")
        _kind(entry.mode, entry.is_dir)
    elif bool(files.is_dir(path)) != bool(expected_dir):
        raise ValueError(f"File type changed: {path}")
    return path


def _children(path, files):
    if files is None:
        with os.scandir(path) as entries:
            for entry in entries:
                info = entry.stat(follow_symlinks=False)
                if stat.S_ISLNK(info.st_mode):
                    continue
                directory = stat.S_ISDIR(info.st_mode)
                if not directory and not stat.S_ISREG(info.st_mode):
                    continue
                yield entry.path, directory
        return
    for entry in files.iterdir_entries(path):
        name = str(entry.name)
        if name in {".", ".."}:
            continue
        if not name or "/" in name or "\x00" in name:
            raise ValueError(f"Unsafe remote lint filename: {name!r}")
        child = str(PurePosixPath(path) / name)
        if _remote_path(entry.path) != child:
            raise ValueError(f"Remote lint listing mismatch: {entry.path}")
        mode = stat.S_IFMT(int(entry.mode or 0))
        if mode not in (0, stat.S_IFREG, stat.S_IFDIR):
            continue
        yield child, _kind(entry.mode, entry.is_dir)


def _read(path, files):
    if files is None:
        _local_root(path, False)
        with open(path, "rb") as stream:
            data = stream.read(MAX_LINT_TEXT_BYTES + 1)
        if len(data) > MAX_LINT_TEXT_BYTES:
            raise ValueError(f"Lint file exceeds size limit: {path}")
        text = decode_text(data, name=path)
    else:
        _remote_root(files, path, False)
        size, _ = files.stat(path)
        if size > MAX_LINT_TEXT_BYTES:
            raise ValueError(f"Lint file exceeds size limit: {path}")
        reader = getattr(files, "read_text_for_edit", files.read_text)
        text = reader(path)
    if not isinstance(text, str) or "\x00" in text:
        raise ValueError(f"Not a supported text file: {path}")
    size = len(text.encode("utf-8"))
    if size > MAX_LINT_TEXT_BYTES:
        raise ValueError(f"Lint text exceeds size limit: {path}")
    return text, size


def collect_documents(selection, catalog, *, files=None, current=lambda: True, tool_only=False):
    """Snapshot selected supported files; bound both discovery and read size."""
    pending = []
    for path, directory in selection:
        _check(current)
        resolved = (_local_root(path, directory) if files is None
                    else _remote_root(files, path, directory))
        pending.append((resolved, bool(directory), True))
    seen = set()
    documents = []
    total = 0
    scanned = 0

    def visit(path, directory, explicit):
        nonlocal total, scanned
        _check(current)
        scanned += 1
        if scanned > MAX_SCAN_ENTRIES:
            raise ValueError(f"Lint discovery exceeds {MAX_SCAN_ENTRIES} entries.")
        if path in seen:
            return
        seen.add(path)
        if directory:
            for child, child_dir in _children(path, files):
                visit(child, child_dir, False)
            return
        packs, tools = catalog.matching(path)
        if not tools and (tool_only or not packs):
            if explicit:
                raise ValueError(f"No installed lint engine supports: {path}")
            return
        if len(documents) >= MAX_FILES:
            raise ValueError(f"Lint selection exceeds {MAX_FILES} supported files.")
        text, size = _read(path, files)
        total += size
        if total > MAX_BATCH_BYTES:
            raise ValueError("Lint selection exceeds the total text size limit.")
        documents.append(Document(path, text))

    for path, directory, explicit in pending:
        visit(path, directory, explicit)
    _check(current)
    if not documents:
        raise ValueError("No supported files found in the lint selection.")
    return tuple(documents)


def _finding(diag, *, plugin_id=""):
    severity = getattr(diag.severity, "value", diag.severity)
    return Finding(str(getattr(diag, "code", getattr(diag, "rule_id", "LINT"))),
                   Severity(severity), str(diag.message),
                   getattr(diag, "line", None), getattr(diag, "column", None),
                   str(getattr(diag, "explanation", "") or ""),
                   str(getattr(diag, "suggested_fix", "") or ""),
                   str(getattr(diag, "source_url", getattr(diag, "documentation_url", "")) or ""),
                   bool(getattr(diag, "is_heuristic", False)))


def lint_documents(documents, catalog, *, current=lambda: True):
    from hpc_gui.plugins.linter_tools import lint_text_with_tool_for

    results = []
    for doc in documents:
        _check(current)
        packs, tools = catalog.matching(doc.path)
        findings = []
        detection = SimpleNamespace(product="unknown", detected_version="")
        for pack in packs:
            _check(current)
            try:
                findings.extend(_finding(d) for d in lint_text(doc.text, file_name=doc.path, rule_pack=pack))
            except Exception as exc:
                findings.append(Finding("ENGINE", Severity.ERROR, f"{pack.plugin_id}: {exc}"))
        for tool in tools:
            _check(current)
            try:
                result = lint_text_with_tool_for(tool, doc.text, file_name=doc.path)
                detection = getattr(result, "detection", None) or detection
                findings.extend(_finding(d) for d in getattr(result, "diagnostics", result))
            except Exception as exc:
                findings.append(Finding("ENGINE", Severity.ERROR, f"{tool.plugin_id}: {exc}"))
        if not packs and not tools:
            findings.append(Finding("ENGINE", Severity.ERROR, "No matching lint engine."))
        results.append(FileResult(doc.path, detection, tuple(findings)))
    _check(current)
    return RunResult(tuple(results))
