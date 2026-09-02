"""Headless transfer workspace joining local and remote wx browser models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.services.transfer_session_controller import TransferSessionController
from hpc_gui.wx_local_files import LocalBrowserModel
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel


@dataclass(frozen=True)
class StorageState:
    name: str
    available: bool
    reason: str = ""


class WxTransferWorkspace:
    def __init__(self, local_path: str | Path, remote_path: str = "/", run_item=None) -> None:
        self.local = LocalBrowserModel(local_path)
        self.remote = WxRemoteDirectoryModel(remote_path)
        self.session = TransferSessionController([], run_item or (lambda item, progress: None))
        self.conflict_policy = "ask"
        self.transfer_mode = "binary"
        self.storage = StorageState("unknown", False, "provider storage facts unavailable")

    def upload_selected(self, paths: list[Path], remote_dir: str) -> int:
        items = [TransferItem("upload", str(path), f"{remote_dir.rstrip('/')}/{path.name}") for path in paths]
        return self.session.engine.enqueue(items) if self.session.engine._thread and self.session.engine._thread.is_alive() else 0

    def download_selected(self, paths: list[str], local_dir: Path) -> tuple[TransferItem, ...]:
        return tuple(TransferItem("download", path, str(local_dir / path.rstrip('/').rsplit('/', 1)[-1])) for path in paths)

    def double_click_local(self, path: Path, remote_dir: str) -> TransferItem:
        return TransferItem("upload", str(path), f"{remote_dir.rstrip('/')}/{path.name}")

    def double_click_remote(self, path: str, local_dir: Path) -> TransferItem:
        return TransferItem("download", path, str(local_dir / path.rstrip('/').rsplit('/', 1)[-1]))

    def cross_pane_clipboard(self, paths: list[str], destination: str, *, move: bool = False) -> TransferItem:
        return TransferItem("download" if not move else "upload", paths[0], destination)

    def drag_operation(self, paths: list[str], destination: str, *, copy: bool = False) -> TransferItem:
        return self.cross_pane_clipboard(paths, destination, move=not copy)

    def set_conflict(self, policy: str) -> None:
        self.session.set_conflict_policy(policy)
        self.conflict_policy = policy

    def set_checksum(self, enabled: bool) -> None:
        self.session.set_checksum_enabled(enabled)

    def set_storage(self, name: str, available: bool, reason: str = "") -> None:
        self.storage = StorageState(name, bool(available), reason)

    def retry_failed(self) -> int:
        return self.session.engine.retry_failed()

    def stop_after_current(self) -> None:
        self.session.engine.stop_after_current()


__all__ = ["StorageState", "WxTransferWorkspace"]
