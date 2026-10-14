"""Persistent favorites and visit history for the local file browser."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from hpc_gui.core.paths import app_data_dir

MAX_LOCAL_HISTORY = 100


def _normalize_path(value: str | Path) -> str:
    return str(Path(value).expanduser().resolve())


def _path_key(value: str | Path) -> str:
    return os.path.normcase(_normalize_path(value))


class LocalNavigationStore:
    """Store local folder favorites and recent visits in app data."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else app_data_dir() / "local-navigation.json"
        self._lock = threading.RLock()
        self._state = self._load()

    def _load(self) -> dict[str, list[dict[str, Any]]]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {"favorites": [], "history": []}
        if not isinstance(payload, dict):
            return {"favorites": [], "history": []}
        favorites = payload.get("favorites")
        history = payload.get("history")
        return {
            "favorites": self._valid_entries(favorites),
            "history": self._valid_entries(history)[:MAX_LOCAL_HISTORY],
        }

    @staticmethod
    def _valid_entries(values: Any) -> list[dict[str, Any]]:
        if not isinstance(values, list):
            return []
        return [
            dict(item)
            for item in values
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        ]

    def _persist(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(
                prefix=self.path.name + ".", suffix=".tmp", dir=self.path.parent
            )
            temp_path = Path(temp_name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as stream:
                    json.dump(self._state, stream, ensure_ascii=False, indent=2)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temp_path, self.path)
            except Exception:
                temp_path.unlink(missing_ok=True)
                raise
        except Exception:
            # Local navigation remains usable if preferences cannot be saved.
            pass

    def favorites(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._state["favorites"]]

    def is_favorite(self, path: str | Path) -> bool:
        target = _path_key(path)
        with self._lock:
            return any(_path_key(item["path"]) == target for item in self._state["favorites"])

    def add_favorite(self, path: str | Path, label: str | None = None) -> None:
        target = _normalize_path(path)
        with self._lock:
            if any(_path_key(item["path"]) == _path_key(target) for item in self._state["favorites"]):
                return
            self._state["favorites"].append(
                {"path": target, "label": label or Path(target).name or target}
            )
            self._persist()

    def remove_favorite(self, path: str | Path) -> None:
        target = _path_key(path)
        with self._lock:
            self._state["favorites"] = [
                item for item in self._state["favorites"]
                if _path_key(item["path"]) != target
            ]
            self._persist()

    def history(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._state["history"]]

    def record_visit(self, path: str | Path) -> None:
        target = _normalize_path(path)
        key = _path_key(target)
        with self._lock:
            recent = [item for item in self._state["history"] if _path_key(item["path"]) != key]
            self._state["history"] = [
                {"path": target, "last_visited": int(time.time())},
                *recent[: MAX_LOCAL_HISTORY - 1],
            ]
            self._persist()

    def clear_history(self) -> None:
        with self._lock:
            self._state["history"] = []
            self._persist()
