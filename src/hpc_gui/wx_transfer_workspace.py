"""Headless transfer workspace joining local and remote wx browser models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.services.transfer_session_controller import TransferSessionController
from hpc_gui.wx_local_files import LocalBrowserModel
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel


@dataclass(frozen=True)
class StorageState:
    name: str
    available: bool
    reason: str = ""


def _supports_resume(files, item) -> bool:
    # Real resumable backends: SSH (seek+append) and FTP (REST/APPE)
    name = type(files).__name__ if files is not None else ""
    if name in ("SSHFilesBackend", "FTPFilesBackend"):
        return True
    # Mock and others generally do not support resume via offset
    if getattr(files, "supports_resume", None) is not None:
        return bool(getattr(files, "supports_resume"))
    # Fallback: inspect backend for known resume markers
    try:
        import inspect
        src = inspect.getsource(type(files))
        if "REST" in src or "APPE" in src or "seek" in src.lower():
            # but mock also may have? exclude mock
            if name == "MockFilesBackend":
                return False
            return True
    except Exception:
        pass
    return False


def create_transfer_conflict_dialog(parent, files, item):
    """Create a purpose-built native wx conflict dialog."""
    try:
        import wx
    except ImportError:
        return None
    resume_supported = _supports_resume(files, item) if files is not None else False
    # Use dedicated dialog instead of generic MessageBox
    title = t("transfer.conflict_title")
    message = t("transfer.conflict_message").format(path=item.dst)
    dlg = wx.Dialog(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    panel = wx.Panel(dlg)
    sizer = wx.BoxSizer(wx.VERTICAL)
    msg = wx.StaticText(panel, label=message)
    msg.Wrap(460)
    sizer.Add(msg, 0, wx.ALL | wx.EXPAND, 12)
    btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
    # Buttons: Overwrite, Skip, Rename, Cancel, optionally Resume
    overwrite = wx.Button(panel, label=t("dirs.conflict_overwrite") if t("dirs.conflict_overwrite") != "[dirs.conflict_overwrite]" else "Overwrite")
    skip = wx.Button(panel, label=t("dirs.conflict_skip") if t("dirs.conflict_skip") != "[dirs.conflict_skip]" else "Skip")
    rename = wx.Button(panel, label=t("dirs.conflict_rename") if t("dirs.conflict_rename") != "[dirs.conflict_rename]" else "Rename")
    cancel = wx.Button(panel, label=t("common.cancel") if t("common.cancel") != "[common.cancel]" else "Cancel")
    resume_btn = None
    if resume_supported:
        resume_btn = wx.Button(panel, label=t("transfer.conflict_resume") if t("transfer.conflict_resume") != "[transfer.conflict_resume]" else "Resume")
    # order: Overwrite, Resume?, Skip, Rename, Cancel
    btn_sizer.Add(overwrite, 0, wx.ALL, 4)
    if resume_btn:
        btn_sizer.Add(resume_btn, 0, wx.ALL, 4)
    btn_sizer.Add(skip, 0, wx.ALL, 4)
    btn_sizer.Add(rename, 0, wx.ALL, 4)
    btn_sizer.Add(cancel, 0, wx.ALL, 4)
    sizer.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 8)
    panel.SetSizer(sizer)
    dlg_sizer = wx.BoxSizer(wx.VERTICAL)
    dlg_sizer.Add(panel, 1, wx.EXPAND)
    dlg.SetSizerAndFit(dlg_sizer)

    result = {"value": "cancel", "rename_target": None}

    def on_overwrite(_event):
        result["value"] = "overwrite"
        dlg.EndModal(wx.ID_OK)

    def on_skip(_event):
        result["value"] = "skip"
        dlg.EndModal(wx.ID_OK)

    def on_cancel(_event):
        result["value"] = "cancel"
        dlg.EndModal(wx.ID_CANCEL)

    def on_resume(_event):
        result["value"] = "resume"
        dlg.EndModal(wx.ID_OK)

    def on_rename(_event):
        # prompt for new name
        target_path = PurePosixPath(item.dst)
        parent_dir = str(target_path.parent) if str(target_path.parent) not in ("", ".") else "/"
        current_name = target_path.name
        while True:
            name_dlg = wx.TextEntryDialog(dlg, t("dirs.rename_label") if t("dirs.rename_label") != "[dirs.rename_label]" else "New name:", t("dirs.rename_title") if t("dirs.rename_title") != "[dirs.rename_title]" else "Rename", current_name)
            try:
                if name_dlg.ShowModal() != wx.ID_OK:
                    result["value"] = "cancel"
                    dlg.EndModal(wx.ID_CANCEL)
                    return
                new_name = name_dlg.GetValue().strip()
                # validation
                if not new_name or new_name in {".", ".."} or "/" in new_name or "\\" in new_name or PurePosixPath(new_name).name != new_name:
                    wx.MessageBox(t("dirs.rename_invalid") if t("dirs.rename_invalid") != "[dirs.rename_invalid]" else "Enter a valid file name without path separators.", t("login.err_title"), wx.OK | wx.ICON_ERROR)
                    continue
                candidate = str(PurePosixPath(parent_dir) / new_name)
                # check existing destination
                exists = False
                try:
                    exists = bool(getattr(files, "exists", lambda _p: False)(candidate))
                except Exception:
                    exists = False
                if exists:
                    wx.MessageBox(t("dirs.new_item_exists").format(path=candidate) if t("dirs.new_item_exists") != "[dirs.new_item_exists]" else f"Exists: {candidate}", t("login.err_title"), wx.OK | wx.ICON_ERROR)
                    continue
                # valid
                result["value"] = ("rename", candidate)
                dlg.EndModal(wx.ID_OK)
                return
            finally:
                name_dlg.Destroy()

    overwrite.Bind(wx.EVT_BUTTON, on_overwrite)
    skip.Bind(wx.EVT_BUTTON, on_skip)
    cancel.Bind(wx.EVT_BUTTON, on_cancel)
    rename.Bind(wx.EVT_BUTTON, on_rename)
    if resume_btn:
        resume_btn.Bind(wx.EVT_BUTTON, on_resume)
    # expose for tests
    dlg._wx_conflict_controls = {"overwrite": overwrite, "skip": skip, "rename": rename, "cancel": cancel, "resume": resume_btn}
    dlg._wx_conflict_result = result
    dlg._wx_conflict_resume_supported = resume_supported
    return dlg


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
        # pre-enqueue check; real safety is in callback re-check
        if state["closed"]:
            return
        try:
            if wx.GetApp() is None:
                return
            wx.CallAfter(callback, *args)
        except BaseException:
            return

    def set_controller(value):
        state["controller"] = value

    def _is_safe():
        if state["closed"]:
            return False
        try:
            if not frame or not wx.Window.FindWindowById(frame.GetId()):
                return False
        except Exception:
            return False
        # also check panel destroyed
        try:
            if not detail or not wx.Window.FindWindowById(detail.GetId()):
                return False
        except Exception:
            return False
        return True

    def update_queue(event, item):
        if not _is_safe():
            return
        try:
            if event == "started":
                detail.SetLabel(t("transfer.active_item").format(item=item.label()))
            elif event == "completed":
                detail.SetLabel(t("transfer.completed_tab"))
            elif event == "failed":
                detail.SetLabel(t("transfer.errors_tab"))
        except RuntimeError:
            return

    def update_progress(item, done, total):
        if not _is_safe():
            return
        try:
            gauge.SetRange(max(1, int(total)))
            gauge.SetValue(min(max(0, int(done)), gauge.GetRange()))
            detail.SetLabel(t("transfer.progress_detail").format(item=item.label(), done=done, total=total, speed="", eta=""))
        except RuntimeError:
            return

    def finish():
        if not _is_safe():
            return
        try:
            controller_value = state["controller"]
            if controller_value and controller_value.engine.failed:
                # check last failure reason
                last = controller_value.engine.failed[-1][1] if controller_value.engine.failed else ""
                if last == "cancelled":
                    detail.SetLabel(t("transfer.cancelled"))
                else:
                    detail.SetLabel(t("transfer.errors_tab"))
            elif controller_value:
                detail.SetLabel(t("transfer.completed_tab"))
            cancel.Disable()
        except RuntimeError:
            return

    def finish_error(message):
        if not _is_safe():
            return
        try:
            detail.SetLabel(t("transfer.errors_tab"))
            cancel.Disable()
        except RuntimeError:
            return

    def cancel_transfer(_event):
        value = state["controller"]
        if value:
            value.cancel()
            if _is_safe():
                try:
                    detail.SetLabel(t("transfer.cancelled"))
                    cancel.Disable()
                except RuntimeError:
                    pass

    def close(_event):
        # mark closed before Destroy to prevent late callbacks touching destroyed controls
        state["closed"] = True
        unsubscribe_language_change(refresh_labels)
        value = state["controller"]
        if value and not value.engine.wait(0):
            value.cancel()
        # Destroy must happen after marking closed
        frame.Destroy()

    def refresh_labels(_language=None):
        if state["closed"]:
            return
        try:
            frame.SetTitle(t("transfer.ftp_activity_title"))
            title.SetLabel(t("transfer.ftp_activity_title"))
            cancel.SetLabel(t("transfer.cancel"))
            # preserve dynamic detail? keep current label as is if it's not terminal static?
            # retranslate terminal/status labels if they are known states
            current = detail.GetLabel()
            # map known translations
            # Instead we update only if detail is one of the known static states, preserve progress detail otherwise
            cv = state["controller"]
            if cv and cv.engine.failed:
                last = cv.engine.failed[-1][1] if cv.engine.failed else ""
                if last == "cancelled":
                    detail.SetLabel(t("transfer.cancelled"))
                else:
                    detail.SetLabel(t("transfer.errors_tab"))
            elif cv and not cv.engine.pending and not cv.engine.failed:
                # completed
                # if detail was showing no_active or completed, update
                if current in (t("transfer.no_active_transfer"), t("transfer.completed_tab"), t("transfer.errors_tab"), t("transfer.cancelled")) or "—" not in current:
                    detail.SetLabel(t("transfer.completed_tab"))
            else:
                # keep existing progress detail
                pass
        except RuntimeError:
            return

    cancel.Bind(wx.EVT_BUTTON, cancel_transfer)
    frame.Bind(wx.EVT_CLOSE, close)
    subscribe_language_change(refresh_labels)
    frame._wx_transfer_controls = {"title": title, "detail": detail, "gauge": gauge, "cancel": cancel}
    frame._wx_transfer_state = state
    frame._wx_transfer_set_controller = set_controller
    # wrap callbacks for safety: each posts a closure that re-checks closed/valid
    def _post_queue(event, item):
        def cb():
            update_queue(event, item)
        post(cb)
    def _post_progress(item, done, total):
        def cb():
            update_progress(item, done, total)
        post(cb)
    def _post_finish():
        def cb():
            finish()
        post(cb)
    frame._wx_transfer_queue = _post_queue
    frame._wx_transfer_progress = _post_progress
    frame._wx_transfer_finish = _post_finish
    frame._wx_transfer_finish_error = lambda msg: post(lambda: finish_error(msg))
    frame._wx_transfer_refresh_labels = refresh_labels
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


__all__ = ["StorageState", "WxTransferWorkspace", "create_transfer_progress", "create_transfer_conflict_dialog", "_supports_resume"]
