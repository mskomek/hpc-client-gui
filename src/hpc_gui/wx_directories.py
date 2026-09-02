"""wx directories workspace model driven by provider storage metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from hpc_gui.wx_remote_files import WxRemoteDirectoryModel


@dataclass(frozen=True)
class StoragePane:
    id: str
    label: str
    path: str


@dataclass(frozen=True)
class BatchSubmitItem:
    index: int
    path: str


class WxDirectoriesWorkspace:
    def __init__(self, storage_metadata: Iterable[dict], *, open_editor=None, submit=None, run_shell=None) -> None:
        self.storages = tuple(
            StoragePane(str(item.get("id", "")), str(item.get("label", item.get("id", ""))), str(item.get("path", "/")))
            for item in storage_metadata
            if item.get("id") and item.get("path")
        )
        self.remote = {pane.id: WxRemoteDirectoryModel(pane.path) for pane in self.storages}
        self._open_editor = open_editor
        self._submit = submit
        self._run_shell = run_shell

    def storage(self, storage_id: str) -> StoragePane:
        return next(item for item in self.storages if item.id == storage_id)

    def double_click(self, path: str, *, is_dir: bool = False) -> str:
        if is_dir and self.remote:
            self.remote[next(iter(self.remote))].navigate(path)
            return "navigate"
        if self._open_editor:
            self._open_editor(path)
        return "view_edit"

    def batch_submit(self, paths: Iterable[str]) -> tuple[BatchSubmitItem, ...]:
        return tuple(BatchSubmitItem(index, path) for index, path in enumerate(paths, 1))

    def submit_item(self, path: str, job_id: str = "") -> None:
        if self._submit:
            self._submit(path, job_id)

    def run_shell(self, path: str) -> None:
        if self._run_shell:
            self._run_shell(path)


__all__ = ["BatchSubmitItem", "StoragePane", "WxDirectoriesWorkspace"]
