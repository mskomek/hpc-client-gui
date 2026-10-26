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
    is_dictionary_name,
    scan_remote_dictionaries,
    scan_remote_mesh_boundaries,
)
from hpc_gui.openfoam_core.cancellation import raise_if_cancelled
from hpc_gui.openfoam_core.remote_paths import (
    remote_lstat_entry,
    require_remote_directory,
    require_remote_regular_file,
)

from .api import lint_files

MAX_FILE_BYTES = MAX_REMOTE_DICTIONARY_BYTES
MAX_CASE_BYTES = MAX_REMOTE_CASE_BYTES
MAX_FILES = MAX_REMOTE_CASE_FILES
MAX_DEPTH = MAX_REMOTE_CASE_DEPTH
SKIP_DIRS = REMOTE_CASE_SKIP_DIRS


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


def lint_remote_path(path: str, files, *, cancel_event=None):
    """Lint a remote case or one dictionary through the active SFTP adapter."""
    selected = PurePosixPath(path)
    root, selected_file = _selected_root(selected, files)
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
        result = lint_files({relative: _read_bytes(files, selected_file, cancel_event=cancel_event)}, case_context=False)
    else:
        result = lint_files(contents, case_context=selected_file is None or bool(contents))
    base = root
    return type(result)(
        tuple(
            replace(item, path=str(base / item.path) if item.path not in ("", "<memory>") else item.path)
            for item in result.diagnostics
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
