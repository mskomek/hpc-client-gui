"""Bounded read-only SFTP lint adapter; remote commands are never executed."""
from __future__ import annotations

from pathlib import Path, PurePosixPath
from dataclasses import replace
import stat
import tempfile

from hpc_gui.openfoam_core import (
    MAX_REMOTE_CASE_BYTES,
    MAX_REMOTE_CASE_DEPTH,
    MAX_REMOTE_CASE_FILES,
    MAX_REMOTE_DICTIONARY_BYTES,
    REMOTE_CASE_SKIP_DIRS,
    DecodedSource,
    Diagnostic,
    SOURCE_DOCS,
    is_dictionary_name,
    scan_remote_dictionaries,
    scan_remote_mesh_boundaries,
    remote_entry_names,
)
from hpc_gui.openfoam_core.cancellation import raise_if_cancelled
from hpc_gui.openfoam_core.remote_paths import (
    remote_lstat_entry,
    require_remote_directory,
    require_remote_regular_file,
)

from .api import _check_release, lint_files
from .shell_scripts import script_diagnostics, script_name_matches

MAX_FILE_BYTES = MAX_REMOTE_DICTIONARY_BYTES
MAX_CASE_BYTES = MAX_REMOTE_CASE_BYTES
MAX_FILES = MAX_REMOTE_CASE_FILES
MAX_DEPTH = MAX_REMOTE_CASE_DEPTH
SKIP_DIRS = REMOTE_CASE_SKIP_DIRS
MAX_REMOTE_SCRIPT_ENTRIES = 4096
MAX_REMOTE_SURFACE_ENTRIES = 64
_SURFACE_SUFFIXES = {".stl", ".obj", ".tri"}


def _remote_mtime(files, path: str) -> float | None:
    try:
        _size, mtime = files.stat(path)
        return float(mtime)
    except (OSError, KeyError, TypeError, ValueError):
        return None


def _remote_mesh_freshness(root: PurePosixPath, files) -> tuple:
    """Report remote surfaces newer than the remote mesh points file."""
    points_time = _remote_mtime(files, str(root / "constant" / "polyMesh" / "points"))
    if points_time is None:
        return ()
    try:
        names, truncated = remote_entry_names(
            files, str(root / "constant" / "triSurface"),
            maximum_entries=MAX_REMOTE_SURFACE_ENTRIES,
        )
    except (OSError, KeyError, NotImplementedError, ValueError):
        return ()
    findings = []
    for name in sorted(names):
        if PurePosixPath(name).suffix.lower() not in _SURFACE_SUFFIXES:
            continue
        path = root / "constant" / "triSurface" / name
        try:
            entry = remote_lstat_entry(files, str(path))
            mode = int(getattr(entry, "mode", 0) or 0)
        except (OSError, KeyError, ValueError):
            continue
        if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
            continue
        surface_time = _remote_mtime(files, str(path))
        if surface_time is None or surface_time <= points_time:
            continue
        findings.append(Diagnostic(
            "OF-CROSS-006", "info", "contextual",
            f"constant/triSurface/{name}", 1, 1,
            f"Surface {name!r} is newer than constant/polyMesh/points; "
            "the mesh may have been generated from older geometry.",
            "Regenerate the mesh from the current surface, or confirm the points file is "
            "intentionally older than the geometry.",
            SOURCE_DOCS, verification_level="contextual",
        ))
    if truncated:
        findings.append(Diagnostic(
            "OF-CROSS-006", "info", "contextual", "constant/triSurface", 1, 1,
            "More remote surfaces were found than the comparison covers; "
            "the remaining files were not inspected.",
            "Reduce the geometry set or compare the remaining surfaces manually.",
            SOURCE_DOCS, verification_level="contextual",
        ))
    return tuple(findings)


def _remote_script_diagnostics(root: PurePosixPath, files, cancel_event=None) -> tuple:
    """Report case-root Allrun/Allclean names from the remote listing only."""
    try:
        names, truncated = remote_entry_names(
            files, str(root), maximum_entries=MAX_REMOTE_SCRIPT_ENTRIES,
        )
    except (OSError, NotImplementedError, ValueError):
        return ()
    raise_if_cancelled(cancel_event)
    matches: list[str] = []
    for name in names:
        raise_if_cancelled(cancel_event)
        if not script_name_matches(name):
            continue
        try:
            entry = remote_lstat_entry(files, str(root / name))
            mode = int(getattr(entry, "mode", 0) or 0)
        except (OSError, ValueError):
            continue
        if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
            continue
        matches.append(name)
    return script_diagnostics(matches, truncated=truncated)


def _read_bytes(files, path: PurePosixPath, *, cancel_event=None) -> bytes:
    raise_if_cancelled(cancel_event)
    require_remote_regular_file(files, str(path), maximum_bytes=MAX_FILE_BYTES)
    size, _mtime = files.stat(str(path))
    if int(size) > MAX_FILE_BYTES:
        raise ValueError(f"remote dictionary exceeds size limit: {path.name}")
    with tempfile.TemporaryDirectory(prefix="hpc-openfoam-lint-") as directory:
        target = Path(directory) / "dictionary"
        files.download(str(path), str(target))
        data = target.read_bytes()
    raise_if_cancelled(cancel_event)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"downloaded dictionary exceeds size limit: {path.name}")
    return data


def _selected_root(path: PurePosixPath, files) -> tuple[PurePosixPath, PurePosixPath | None]:
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("remote OpenFOAM path must be a safe absolute POSIX path")
    try:
        selected = remote_lstat_entry(files, str(path))
    except NotImplementedError as exc:
        raise ValueError("remote backend cannot verify symbolic links") from exc
    except OSError:
        selected = None
    if selected is not None and stat.S_ISLNK(int(getattr(selected, "mode", 0) or 0)):
        raise ValueError("symbolic links are not followed by the remote linter")
    if selected is not None and stat.S_ISDIR(int(getattr(selected, "mode", 0) or 0)):
        require_remote_directory(files, str(path))
        return path, None
    if not is_dictionary_name(path.name):
        raise ValueError("selected remote path is not a case folder or dictionary")
    if selected is not None:
        require_remote_regular_file(files, str(path), maximum_bytes=MAX_FILE_BYTES)
    for index, part in enumerate(path.parts):
        if part in {"system", "constant", "0", "0.orig"}:
            root = PurePosixPath(*path.parts[:index])
            if root.is_absolute():
                return root, path
    return path.parent, path


def lint_remote_path(path: str, files, *, cancel_event=None, release: str | None = None):
    """Lint a remote case or one dictionary through the active SFTP adapter."""
    _check_release(release)
    selected = PurePosixPath(path)
    root, selected_file = _selected_root(selected, files)
    script_findings = _remote_script_diagnostics(root, files, cancel_event)
    freshness = _remote_mesh_freshness(root, files)
    contents = scan_remote_dictionaries(
        str(root),
        files,
        maximum_file_bytes=MAX_FILE_BYTES,
        maximum_case_bytes=MAX_CASE_BYTES,
        maximum_files=MAX_FILES,
        maximum_depth=MAX_DEPTH,
        skip_dirs=SKIP_DIRS,
        cancel_event=cancel_event,
    )
    if selected_file is None or "0" in selected_file.parts or "0.orig" in selected_file.parts:
        contents.update(scan_remote_mesh_boundaries(
            str(root),
            files,
            maximum_case_bytes=max(0, MAX_CASE_BYTES - sum(len(data) for data in contents.values())),
            maximum_files=max(0, MAX_FILES - len(contents)),
            cancel_event=cancel_event,
        ))
    if selected_file is not None:
        relative = selected_file.relative_to(root).as_posix() if root in selected_file.parents else ""
        if relative and relative not in contents:
            contents[relative] = _read_bytes(files, selected_file, cancel_event=cancel_event)
    if not contents and selected_file is not None:
        relative = selected_file.relative_to(root).as_posix() if root in selected_file.parents else selected_file.name
        result = lint_files(
            {relative: _read_bytes(files, selected_file, cancel_event=cancel_event)},
            case_context=False, release=release,
        )
    else:
        result = lint_files(
            contents, case_context=selected_file is None or bool(contents), release=release,
        )
    base = root

    def _prefixed(path: str) -> str:
        # Pseudo-paths such as <scripts:cap> are markers, not case files.
        if path in ("", "<memory>") or path.startswith("<"):
            return path
        return str(base / path)

    return type(result)(
        tuple(
            replace(item, path=_prefixed(item.path))
            for item in result.diagnostics
        ) + tuple(
            replace(item, path=_prefixed(item.path))
            for item in script_findings
        ) + tuple(
            replace(item, path=_prefixed(item.path))
            for item in freshness
        ),
        tuple(str(base / relative) for relative in result.files_checked),
        level=result.level,
        edition=result.edition,
        version=result.version,
    )


def read_remote_dictionary_text(path: str, files) -> str:
    """Read one bounded regular SFTP dictionary for editor navigation."""
    selected = PurePosixPath(path)
    if not selected.is_absolute() or ".." in selected.parts or not is_dictionary_name(selected.name):
        raise ValueError("remote finding path is not a safe dictionary path")
    data = _read_bytes(files, selected)
    return DecodedSource.from_bytes(data).text
