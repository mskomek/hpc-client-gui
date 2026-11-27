"""Bridge background upload planning to GUI confirmation and queue ownership."""
from __future__ import annotations

from hpc_gui.core.i18n import t
from hpc_gui.services.upload_plan import build_upload_plan, transfer_limits


def prepare_upload(session_state, lifecycle, parent, session, files, paths,
                   destination, start_transfer, *, generation):
    """Called by the planner worker; post confirmation/start to the GUI thread."""
    items = build_upload_plan(paths, destination)
    if not items:
        return

    def still_current():
        current = session_state.get("session")
        if (current is not session or not current or current.get("files") is not files
                or session_state.get("generation") != generation
                or getattr(lifecycle, "shutdown_started", False)):
            return False
        if parent is None:
            return True
        try:
            return not parent.IsBeingDeleted()
        except RuntimeError:
            return False

    def start():
        if not still_current():
            return
        try:
            if parent is not None:
                from hpc_gui.wx_upload_preflight import confirm_upload_plan
                _, effective = transfer_limits(files, session.get("profile"))
                if not confirm_upload_plan(parent, items, effective, still_current=still_current):
                    return
            if still_current():
                start_transfer(session_state, lifecycle, items, files_backend=files, parent=parent)
        except Exception as exc:
            if parent is None:
                raise
            if still_current():
                import wx
                wx.MessageBox(str(exc), t("login.err_title"), wx.OK | wx.ICON_ERROR, parent)

    if parent is None:
        start()
    else:
        import wx
        if wx.IsMainThread():
            start()
        else:
            wx.CallAfter(start)
