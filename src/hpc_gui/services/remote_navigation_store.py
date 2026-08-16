"""Per-profile remote favorites and navigation history, encrypted at rest.

Remote paths say where a user's work lives, so this state never lands in
``config.json`` as plaintext.  Each profile gets one file under
``~/.truba_slurm_gui/private/`` encrypted with an OS-held secret: DPAPI on
Windows, an OS keyring entry elsewhere.  When neither is reachable the feature
reports itself unavailable instead of falling back to plaintext.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core import secret_store

MAX_HISTORY = 100
SCHEMA_VERSION = 1
_MAGIC = b"HPCNAV1\n"
_KEYRING_SERVICE = "hpc-client-gui"
_KEYRING_USERNAME = "remote-navigation"


def _private_dir() -> Path:
    d = Path.home() / ".truba_slurm_gui" / "private"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _state_path(profile_id: str) -> Path:
    return _private_dir() / f"{profile_id}.bin"


def _fernet():
    """Return a Fernet bound to a key held by the OS keyring, or None."""
    try:
        import keyring
        from cryptography.fernet import Fernet
    except Exception:
        return None
    try:
        key = keyring.get_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
        if not key:
            key = Fernet.generate_key().decode("ascii")
            keyring.set_password(_KEYRING_SERVICE, _KEYRING_USERNAME, key)
        return Fernet(key.encode("ascii"))
    except Exception:
        return None


def is_available() -> bool:
    """Whether private profile state can be stored encrypted on this machine."""
    return secret_store.is_available() or _fernet() is not None


def _encrypt(payload: Dict[str, Any]) -> bytes:
    raw = json.dumps(payload, ensure_ascii=False)
    if secret_store.is_available():
        return _MAGIC + secret_store.protect_secret(raw).encode("ascii")
    fernet = _fernet()
    if fernet is None:
        raise RuntimeError("no OS-held secret available for private profile state")
    return _MAGIC + fernet.encrypt(raw.encode("utf-8"))


def _decrypt(blob: bytes) -> Dict[str, Any]:
    if not blob.startswith(_MAGIC):
        raise ValueError("unrecognised private profile state")
    body = blob[len(_MAGIC) :]
    if secret_store.is_available():
        raw = secret_store.unprotect_secret(body.decode("ascii"))
    else:
        fernet = _fernet()
        if fernet is None:
            raise RuntimeError("no OS-held secret available for private profile state")
        raw = fernet.decrypt(body).decode("utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("unrecognised private profile state")
    return data


def _normalize(path: str) -> str:
    return (path or "/").rstrip("/") or "/"


def _basename(path: str) -> str:
    clean = _normalize(path)
    return clean.rsplit("/", 1)[-1] or clean


def delete_profile_navigation(profile_id: str) -> None:
    """Remove a profile's private state; called when the profile is deleted."""
    with _INSTANCES_LOCK:
        _INSTANCES.pop(profile_id, None)
    try:
        _state_path(profile_id).unlink(missing_ok=True)
    except Exception:
        pass


class RemoteNavigationStore:
    """Favorites and history for one profile, shared by every remote panel."""

    def __init__(self, profile_id: str) -> None:
        self.profile_id = profile_id
        self._lock = threading.RLock()
        self._state = self._load()

    # ---- persistence ----------------------------------------------------
    def _load(self) -> Dict[str, Any]:
        empty = {"schema_version": SCHEMA_VERSION, "favorites": [], "history": []}
        path = _state_path(self.profile_id)
        try:
            blob = path.read_bytes()
        except FileNotFoundError:
            return empty
        except Exception:
            return empty
        try:
            data = _decrypt(blob)
        except Exception:
            # Tampered, truncated, or written under a key we no longer hold.
            # Losing bookmarks beats guessing at damaged private state.
            return empty
        favorites = data.get("favorites")
        history = data.get("history")
        return {
            "schema_version": SCHEMA_VERSION,
            "favorites": favorites if isinstance(favorites, list) else [],
            "history": history if isinstance(history, list) else [],
        }

    def _save(self) -> None:
        path = _state_path(self.profile_id)
        blob = _encrypt(self._state)
        fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(blob)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    def _persist(self) -> None:
        try:
            self._save()
        except Exception:
            # A failed write must not break navigation; the in-memory list
            # stays correct for this session.
            pass

    # ---- favorites ------------------------------------------------------
    def favorites(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._state["favorites"]]

    def is_favorite(self, path: str) -> bool:
        target = _normalize(path)
        with self._lock:
            return any(_normalize(item.get("path", "")) == target for item in self._state["favorites"])

    def add_favorite(self, path: str, kind: str = "directory", label: Optional[str] = None) -> None:
        target = _normalize(path)
        with self._lock:
            if self.is_favorite(target):
                return
            self._state["favorites"].append(
                {
                    "id": str(uuid.uuid4()),
                    "path": target,
                    "label": (label or _basename(target)),
                    "kind": "file" if kind == "file" else "directory",
                }
            )
            self._persist()

    def remove_favorite(self, path: str) -> None:
        target = _normalize(path)
        with self._lock:
            kept = [
                item
                for item in self._state["favorites"]
                if _normalize(item.get("path", "")) != target
            ]
            if len(kept) == len(self._state["favorites"]):
                return
            self._state["favorites"] = kept
            self._persist()

    def toggle_favorite(self, path: str, kind: str = "directory") -> bool:
        """Add or remove; returns whether the path is a favorite afterwards."""
        with self._lock:
            if self.is_favorite(path):
                self.remove_favorite(path)
                return False
            self.add_favorite(path, kind)
            return True

    # ---- history --------------------------------------------------------
    def history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._state["history"]]

    def record_visit(self, path: str) -> None:
        """Record a directory that was opened successfully."""
        target = _normalize(path)
        with self._lock:
            entries = [
                item
                for item in self._state["history"]
                if _normalize(item.get("path", "")) != target
            ]
            entries.insert(0, {"path": target, "last_visited": int(time.time())})
            self._state["history"] = entries[:MAX_HISTORY]
            self._persist()

    def clear_history(self) -> None:
        with self._lock:
            if not self._state["history"]:
                return
            self._state["history"] = []
            self._persist()


_INSTANCES: Dict[str, RemoteNavigationStore] = {}
_INSTANCES_LOCK = threading.RLock()


def navigation_store_for_profile(profile_id: str) -> Optional[RemoteNavigationStore]:
    """Return the one store for this profile, so every panel shares its state."""
    if not profile_id or not is_available():
        return None
    with _INSTANCES_LOCK:
        store = _INSTANCES.get(profile_id)
        if store is None:
            store = RemoteNavigationStore(profile_id)
            _INSTANCES[profile_id] = store
        return store
