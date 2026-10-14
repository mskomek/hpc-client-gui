"""Encrypted per-profile identities for interrupted file transfers."""

from __future__ import annotations

import hashlib
import os
import threading
import time
from functools import lru_cache
from typing import Any

from hpc_gui.config.storage import get_profile_id, load_profiles

from .private_profile_data import (
    delete_private_profile_data,
    is_private_profile_data_available,
    load_private_profile_data,
    save_private_profile_data,
)

_NAMESPACE = "transfer-resume"
_SCHEMA_VERSION = 1
_MAX_RECORDS = 500
_MAX_AGE_SECONDS = 60 * 60 * 24 * 90
_CHECKPOINT_BYTES = 8 * 1024 * 1024
_STORES: dict[str, "TransferResumeStore"] = {}
_STORES_LOCK = threading.RLock()


def _updated_at(record: dict[str, Any]) -> int:
    try:
        return int(record.get("updated_at", 0) or 0)
    except (TypeError, ValueError):
        return 0


def profile_id_for_backend(files: Any) -> str:
    """Find the saved connection profile that owns this files backend.

    Backends created by the GUI and CLI carry the same endpoint data as their
    saved profile. Ambiguous endpoints deliberately return no profile so a
    transfer never resumes against another profile's private state.
    """
    explicit = str(getattr(files, "profile_id", "") or "").strip()
    if explicit:
        return explicit
    ssh = getattr(files, "ssh", None)
    info = getattr(ssh, "info", None)
    host = getattr(info, "host", "") or getattr(files, "_host", "")
    username = getattr(info, "username", "") or getattr(files, "_username", "")
    port = getattr(info, "port", None) or getattr(files, "_port", None)
    if not host or not username or port is None:
        return ""

    def clean_host(value: Any) -> str:
        return str(value or "").strip().rstrip(".").casefold()

    profile_id = _profile_id_for_endpoint(
        clean_host(host), str(username).strip(), _coerce_port(port)
    )
    if profile_id:
        try:
            files.profile_id = profile_id
        except Exception:
            pass
    return profile_id


def _coerce_port(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


@lru_cache(maxsize=128)
def _profile_id_for_endpoint(host: str, username: str, port_value: int) -> str:
    if not host or not username or port_value < 1:
        return ""
    matches = [
        profile
        for profile in load_profiles()
        if str(profile.get("host", "")).strip().rstrip(".").casefold() == host
        and str(profile.get("username", "")).strip() == username
        and _coerce_port(profile.get("port", 22) or 22) == port_value
    ]
    if len(matches) != 1:
        return ""
    profile = matches[0]
    return str(
        profile.get("id")
        or get_profile_id(str(profile.get("name") or ""))
        or ""
    )


def transfer_record_key(direction: str, target_path: str) -> str:
    """Stable key per destination; identity fields guard against stale reuse."""
    target = os.path.normcase(os.path.abspath(target_path)) if direction == "download" else str(target_path)
    raw = f"{direction}\0{target}".encode("utf-8", errors="surrogatepass")
    return hashlib.sha256(raw).hexdigest()


def local_file_identity(path: str) -> dict[str, Any]:
    """Describe the source without storing file data beside it."""
    source = os.path.abspath(os.path.expanduser(path))
    stat = os.stat(source)
    digest = hashlib.sha256()
    with open(source, "rb") as stream:
        digest.update(stream.read(64 * 1024))
        if stat.st_size > 64 * 1024:
            stream.seek(max(0, stat.st_size - 64 * 1024))
            digest.update(stream.read(64 * 1024))
    return {
        "local_path": source,
        "size": int(stat.st_size),
        "mtime_ns": int(getattr(stat, "st_mtime_ns", stat.st_mtime * 1e9)),
        "ctime_ns": int(getattr(stat, "st_ctime_ns", stat.st_ctime * 1e9)),
        "file_id": int(getattr(stat, "st_ino", 0) or 0),
        "edge_sha256": digest.hexdigest(),
    }


def progress_with_resume_checkpoints(
    registry: "TransferResumeStore | None",
    key: str,
    identity: dict[str, Any],
    partial_path: str,
    progress_cb,
):
    """Persist byte offsets periodically, then forward normal UI progress."""
    if registry is None and not callable(progress_cb):
        return None
    last_saved = 0

    def report(done: int, total: int) -> None:
        nonlocal last_saved
        done = max(0, int(done))
        if registry and (
            done - last_saved >= _CHECKPOINT_BYTES
            or (total > 0 and done >= total)
        ):
            try:
                registry.save(key, identity, partial_path, done)
                last_saved = done
            except Exception:
                last_saved = done
        if callable(progress_cb):
            progress_cb(done, total)

    return report


class TransferResumeStore:
    """A small encrypted registry; partial byte counts live with the partial."""

    def __init__(self, profile_id: str) -> None:
        self.profile_id = profile_id
        self._lock = threading.RLock()
        self._state = load_private_profile_data(
            profile_id,
            _NAMESPACE,
            {"schema_version": _SCHEMA_VERSION, "records": {}},
        )
        if not isinstance(self._state.get("records"), dict):
            self._state = {"schema_version": _SCHEMA_VERSION, "records": {}}

    def get(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            value = self._state["records"].get(key)
            return dict(value) if isinstance(value, dict) else None

    def save(
        self,
        key: str,
        identity: dict[str, Any],
        partial_path: str,
        partial_bytes: int,
    ) -> None:
        now = int(time.time())
        with self._lock:
            records = self._state["records"]
            records[key] = {
                "identity": dict(identity),
                "partial_path": str(partial_path),
                "partial_bytes": max(0, int(partial_bytes)),
                "updated_at": now,
            }
            cutoff = now - _MAX_AGE_SECONDS
            records = {
                record_key: record
                for record_key, record in records.items()
                if isinstance(record, dict)
                and _updated_at(record) >= cutoff
            }
            if len(records) > _MAX_RECORDS:
                records = dict(
                    sorted(
                        records.items(),
                        key=lambda item: _updated_at(item[1]),
                        reverse=True,
                    )[:_MAX_RECORDS]
                )
            self._state["records"] = records
            save_private_profile_data(self.profile_id, _NAMESPACE, self._state)

    def remove(self, key: str) -> None:
        with self._lock:
            if key not in self._state["records"]:
                return
            del self._state["records"][key]
            if self._state["records"]:
                save_private_profile_data(self.profile_id, _NAMESPACE, self._state)
            else:
                delete_private_profile_data(self.profile_id, _NAMESPACE)


def transfer_resume_store_for_backend(files: Any) -> TransferResumeStore | None:
    try:
        profile_id = profile_id_for_backend(files)
        available = is_private_profile_data_available()
    except Exception:
        return None
    if not profile_id or not available:
        return None
    try:
        with _STORES_LOCK:
            store = _STORES.get(profile_id)
            if store is None:
                store = TransferResumeStore(profile_id)
                _STORES[profile_id] = store
            return store
    except Exception:
        return None


def delete_profile_transfer_resume(profile_id: str) -> None:
    with _STORES_LOCK:
        _STORES.pop(str(profile_id or ""), None)
    try:
        delete_private_profile_data(str(profile_id or ""), _NAMESPACE)
    except Exception:
        pass
