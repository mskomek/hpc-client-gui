"""Transfer a read-only remote download plan to the native queue owner."""
from __future__ import annotations

from hpc_gui.core.i18n import t
from hpc_gui.services.download_plan import build_download_plan
from hpc_gui.services.transfer_controller import TransferCancelled


def prepare_download(session_state, lifecycle, parent, session, files, paths,
                     destination, start_transfer, *, generation):
    def current():
        return (session_state.get("session") is session
                and session.get("files") is files
                and session_state.get("generation") == generation
                and not getattr(lifecycle, "shutdown_started", False))

    try:
        items = build_download_plan(files, paths, destination, current=current)
    except TransferCancelled:
        return
    if not items or not current():
        return

    def start():
        if not current():
            return
        if parent is not None:
            try:
                if parent.IsBeingDeleted():
                    return
            except RuntimeError:
                return
        try:
            start_transfer(session_state, lifecycle, items, files_backend=files, parent=parent)
        except Exception as exc:
            if parent is None:
                raise
            if current():
                import wx
                wx.MessageBox(str(exc), t("login.err_title"), wx.OK | wx.ICON_ERROR, parent)

    if parent is None:
        start()
    else:
        import wx
        wx.CallAfter(start)
