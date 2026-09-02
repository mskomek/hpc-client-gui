"""wx remote-directory model with non-blocking-adapter contracts."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Callable, Iterable

from hpc_gui.services.remote_directory_controller import ListingRequest, RemoteDirectoryController


@dataclass(frozen=True)
class RemoteEntry:
    path: str
    is_dir: bool = False
    size: int = 0


@dataclass(frozen=True)
class PermissionRequest:
    path: str
    owner: int
    group: int
    others: int
    special: int = 0
    recursive: bool = False


@dataclass(frozen=True)
class RemoteOperation:
    kind: str
    paths: tuple[str, ...]
    destination: str = ""


class WxRemoteDirectoryModel(RemoteDirectoryController):
    def __init__(self, initial_path: str = "/", cache_ttl: float = 60.0) -> None:
        super().__init__(initial_path)
        self.tabs = [self.current_path]
        self.active_tab = 0
        self.cache_ttl = max(0.0, float(cache_ttl))
        self._cache: dict[str, tuple[float, tuple[RemoteEntry, ...]]] = {}
        self.selected: tuple[str, ...] = ()

    def list_entries(self, loader: Callable[[str], Iterable[RemoteEntry]], *, force: bool = False) -> tuple[RemoteEntry, ...]:
        key = self._normalize(self.current_path)
        cached = self._cache.get(key)
        if not force and cached and time.monotonic() - cached[0] <= self.cache_ttl:
            return cached[1]
        entries = tuple(loader(key))
        self._cache[key] = (time.monotonic(), entries)
        return entries

    def invalidate(self, path: str | None = None) -> None:
        if path is None:
            self._cache.clear()
        else:
            self._cache.pop(self._normalize(path), None)

    def batched(self, entries: Iterable[RemoteEntry], batch_size: int = 200) -> tuple[tuple[RemoteEntry, ...], ...]:
        values = tuple(entries)
        size = max(1, int(batch_size))
        return tuple(values[index:index + size] for index in range(0, len(values), size))

    def navigate(self, path: str) -> ListingRequest:
        request = super().navigate(str(PurePosixPath(path)))
        self.tabs[self.active_tab] = self.current_path
        return request

    def new_tab(self, path: str) -> int:
        target = self._normalize(str(PurePosixPath(path)))
        self.tabs.append(target)
        self.active_tab = len(self.tabs) - 1
        self.current_path = target
        return self.active_tab

    def middle_click(self, path: str) -> int:
        return self.new_tab(path)

    @staticmethod
    def context_action(action: str, paths: Iterable[str], destination: str = "") -> RemoteOperation:
        return WxRemoteDirectoryModel.operation(action, paths, destination)

    @staticmethod
    def operation(kind: str, paths: Iterable[str], destination: str = "") -> RemoteOperation:
        if kind not in {"copy", "move", "delete", "rename", "create", "undo"}:
            raise ValueError(kind)
        return RemoteOperation(kind, tuple(str(path) for path in paths), destination)

    @staticmethod
    def permission_request(path: str, *, owner: int, group: int, others: int, special: int = 0, recursive: bool = False) -> PermissionRequest:
        if recursive:
            raise ValueError("recursive permissions are disabled")
        if any(value < 0 or value > 7 for value in (owner, group, others)) or special < 0 or special > 7:
            raise ValueError("invalid permission bits")
        return PermissionRequest(path, owner, group, others, special)

    @staticmethod
    def clipboard_payload(paths: Iterable[str]) -> str:
        return "\r\n".join(str(path) for path in paths)


__all__ = ["PermissionRequest", "RemoteEntry", "RemoteOperation", "WxRemoteDirectoryModel"]
