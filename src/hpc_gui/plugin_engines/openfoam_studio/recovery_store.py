"""Persistent metadata for interrupted remote Case Studio saves.

Only validated remote recovery artifact paths are stored. Credentials and
dictionary contents remain in their existing stores.
"""
from __future__ import annotations

import hashlib
import re
import threading
import time
from pathlib import PurePosixPath
from typing import Any

from hpc_gui.openfoam_core import safe_relative_path
from hpc_gui.services.private_profile_data import (
    delete_private_profile_data,
    is_private_profile_data_available,
    load_private_profile_data,
    save_private_profile_data,
)
from hpc_gui.services.transfer_resume_store import profile_id_for_backend

_NAMESPACE = "openfoam-save-recovery"
_SCHEMA_VERSION = 1
_MAX_AGE_SECONDS = 90 * 24 * 60 * 60
_MAX_RECORDS = 100
_MAX_PATHS = 1024
_ARTIFACT_NAME = re.compile(r"^\.(?P<name>[^/]+)\.[0-9a-f]{32}\.(?:backup|stage)$")
_LOCKS: dict[str, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()


def recovery_profile_id(files: Any) -> str:
    """Return the saved connection identity for a backend, if unambiguous."""
    try:
        return profile_id_for_backend(files)
    except Exception:
        return ""


def _lock_for(profile_id: str) -> threading.RLock:
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(profile_id, threading.RLock())


def _root(value: str) -> str:
    root = PurePosixPath(str(value))
    if not root.is_absolute() or ".." in root.parts or len(str(root)) > 4096:
        raise ValueError("remote case root must be a safe absolute POSIX path")
    return str(root)


def _valid_paths(root: str, paths: Any) -> tuple[str, ...]:
    if not isinstance(paths, (list, tuple)) or not 0 < len(paths) <= _MAX_PATHS:
        return ()
    base = PurePosixPath(root)
    result: list[str] = []
    for raw in paths:
        path = PurePosixPath(str(raw))
        match = _ARTIFACT_NAME.fullmatch(path.name)
        if not path.is_absolute() or ".." in path.parts or base not in path.parents or not match:
            return ()
        target = path.with_name(match.group("name"))
        try:
            relative = target.relative_to(base).as_posix()
        except ValueError:
            return ()
        if not safe_relative_path(relative):
            return ()
        result.append(str(path))
    return tuple(dict.fromkeys(result))


def _record_key(root: str) -> str:
    return hashlib.sha256(root.encode("utf-8")).hexdigest()


def _record_time(record: Any) -> int:
    try:
        return int(record.get("updated_at", 0) or 0) if isinstance(record, dict) else 0
    except (TypeError, ValueError):
        return 0


class RemoteSaveRecoveryStore:
    """Encrypted per-profile index of remote stage/backup paths."""

    def __init__(self, profile_id: str) -> None:
        self.profile_id = str(profile_id)
        if not self.profile_id:
            raise ValueError("a saved connection profile is required")
        self._lock = _lock_for(self.profile_id)

    def _load(self) -> dict[str, Any]:
        state = load_private_profile_data(
            self.profile_id,
            _NAMESPACE,
            {"schema_version": _SCHEMA_VERSION, "records": {}},
        )
        if not isinstance(state, dict):
            return {"schema_version": _SCHEMA_VERSION, "records": {}}
        records = state.get("records")
        if state.get("schema_version") != _SCHEMA_VERSION or not isinstance(records, dict):
            return {"schema_version": _SCHEMA_VERSION, "records": {}}
        return {"schema_version": _SCHEMA_VERSION, "records": records}

    def get(self, case_root: str) -> tuple[str, ...]:
        root = _root(case_root)
        with self._lock:
            record = self._load()["records"].get(_record_key(root))
        if not isinstance(record, dict) or record.get("root") != root:
            return ()
        try:
            updated = int(record.get("updated_at", 0))
        except (TypeError, ValueError):
            return ()
        if updated < int(time.time()) - _MAX_AGE_SECONDS:
            return ()
        return _valid_paths(root, record.get("paths"))

    def save(self, case_root: str, paths: Any) -> None:
        root = _root(case_root)
        safe_paths = _valid_paths(root, paths)
        if not safe_paths:
            raise ValueError("remote recovery paths are invalid")
        now = int(time.time())
        key = _record_key(root)
        with self._lock:
            state = self._load()
            records = {
                name: record
                for name, record in state["records"].items()
                if isinstance(record, dict)
                and _record_time(record) >= now - _MAX_AGE_SECONDS
            }
            records[key] = {"root": root, "paths": list(safe_paths), "updated_at": now}
            if len(records) > _MAX_RECORDS:
                records = dict(
                    sorted(records.items(), key=lambda item: _record_time(item[1]), reverse=True)[
                        :_MAX_RECORDS
                    ]
                )
            save_private_profile_data(
                self.profile_id,
                _NAMESPACE,
                {"schema_version": _SCHEMA_VERSION, "records": records},
            )

    def remove(self, case_root: str) -> None:
        root = _root(case_root)
        key = _record_key(root)
        with self._lock:
            state = self._load()
            records = state["records"]
            if key not in records:
                return
            records.pop(key, None)
            if records:
                save_private_profile_data(
                    self.profile_id,
                    _NAMESPACE,
                    {"schema_version": _SCHEMA_VERSION, "records": records},
                )
            else:
                delete_private_profile_data(self.profile_id, _NAMESPACE)


def recovery_store_for_backend(files: Any) -> RemoteSaveRecoveryStore | None:
    """Resolve an encrypted store only when this backend maps to one profile."""
    profile_id = recovery_profile_id(files)
    if not profile_id:
        return None
    try:
        if not is_private_profile_data_available():
            return None
        return RemoteSaveRecoveryStore(profile_id)
    except Exception:
        return None
