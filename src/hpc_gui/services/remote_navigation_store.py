"""Per-profile remote favorites and navigation history, encrypted at rest.

Remote paths say where a user's work lives, so this state never lands in
``config.json`` as plaintext.  Each profile gets one file under
``~/.truba_slurm_gui/private/`` encrypted with an OS-held secret: DPAPI on
Windows, an OS keyring entry elsewhere.  When neither is reachable the feature
reports itself unavailable instead of falling back to plaintext.
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from .private_profile_data import (
    delete_private_profile_data,
    is_private_profile_data_available,
    load_private_profile_data,
    save_private_profile_data,
)

MAX_HISTORY = 100
SCHEMA_VERSION = 1


def is_available() -> bool:
    """Whether private profile state can be stored encrypted on this machine."""
    return is_private_profile_data_available()


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
        delete_private_profile_data(profile_id, "navigation")
    except Exception:
        pass
    try:
        from .transfer_resume_store import delete_profile_transfer_resume

        delete_profile_transfer_resume(profile_id)
    except Exception:
        try:
            delete_private_profile_data(profile_id, "transfer-resume")
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
        data = load_private_profile_data(self.profile_id, "navigation", empty)
        favorites = data.get("favorites")
        history = data.get("history")
        return {
            "schema_version": SCHEMA_VERSION,
            "favorites": favorites if isinstance(favorites, list) else [],
            "history": history if isinstance(history, list) else [],
        }

    def _save(self) -> None:
        save_private_profile_data(self.profile_id, "navigation", self._state)

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
