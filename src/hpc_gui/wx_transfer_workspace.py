"""Headless transfer workspace joining local and remote wx browser models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hpc_gui.core.i18n import t
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.services.transfer_session_controller import TransferSessionController
from hpc_gui.wx_local_files import LocalBrowserModel
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel


@dataclass(frozen=True)
class StorageState:
    name: str
    available: bool
    reason: str = ""


def create_transfer_progress(parent, controller=None):
    """Create the small wx owner for a transfer session, if wx is available."""
    try:
        import wx
    except ImportError:
        return None

    frame = wx.Frame(parent, title=t("transfer.ftp_activity_title"), size=(520, 150))
    panel = wx.Panel(frame)
    title = wx.StaticText(panel, label=t("transfer.ftp_activity_title"))
    detail = wx.StaticText(panel, label=t("transfer.no_active_transfer"))
    gauge = wx.Gauge(panel, range=1)
    cancel = wx.Button(panel, label=t("transfer.cancel"))
    layout = wx.BoxSizer(wx.VERTICAL)
    layout.Add(title, 0, wx.ALL | wx.EXPAND, 8)
    layout.Add(detail, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 8)
    layout.Add(gauge, 0, wx.ALL | wx.EXPAND, 8)
    layout.Add(cancel, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    panel.SetSizer(layout)
    state = {"closed": False, "controller": controller}

    def post(callback, *args):
        if state["closed"]:
            return
        try:
            wx.CallAfter(callback, *args)
        except (AssertionError, RuntimeError):
            return

    def set_controller(value):
        state["controller"] = value

    def update_queue(event, item):
        if event == "started":
            detail.SetLabel(t("transfer.active_item").format(item=item.label()))
        elif event == "completed":
            detail.SetLabel(t("transfer.completed_tab"))
        elif event == "failed":
            detail.SetLabel(t("transfer.errors_tab"))

    def update_progress(item, done, total):
        gauge.SetRange(max(1, int(total)))
        gauge.SetValue(min(max(0, int(done)), gauge.GetRange()))
        detail.SetLabel(t("transfer.progress_detail").format(item=item.label(), done=done, total=total, speed="", eta=""))

    def finish():
        if state["closed"]:
            return
        controller_value = state["controller"]
        if controller_value and controller_value.engine.failed:
            detail.SetLabel(t("transfer.cancelled") if controller_value.engine.failed[-1][1] == "cancelled" else t("transfer.errors_tab"))
        elif controller_value:
            detail.SetLabel(t("transfer.completed_tab"))
        cancel.Disable()

    def cancel_transfer(_event):
        value = state["controller"]
        if value:
            value.cancel()
            detail.SetLabel(t("transfer.cancelled"))
            cancel.Disable()

    def close(_event):
        state["closed"] = True
        value = state["controller"]
        if value and not value.engine.wait(0):
            value.cancel()
        frame.Destroy()

    cancel.Bind(wx.EVT_BUTTON, cancel_transfer)
    frame.Bind(wx.EVT_CLOSE, close)
    frame._wx_transfer_controls = {"title": title, "detail": detail, "gauge": gauge, "cancel": cancel}
    frame._wx_transfer_state = state
    frame._wx_transfer_set_controller = set_controller
    frame._wx_transfer_queue = lambda event, item: post(update_queue, event, item)
    frame._wx_transfer_progress = lambda item, done, total: post(update_progress, item, done, total)
    frame._wx_transfer_finish = lambda: post(finish)
    frame.Show()
    return frame


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
