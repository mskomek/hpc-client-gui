"""Worker-to-native-dialog bridge with cancellation and owner invalidation."""
from __future__ import annotations

from threading import Event


def request_conflict_decision(parent, files, item, current, metadata):
    import wx

    from hpc_gui.wx_transfer_conflict_dialog import create_wx_transfer_conflict_dialog

    ready = Event()
    result = {"value": "cancel"}

    def parent_alive():
        try:
            return parent is not None and not parent.IsBeingDeleted()
        except RuntimeError:
            return False

    def ask():
        dialog = None
        timer = None
        try:
            if not current() or not parent_alive():
                return
            dialog = create_wx_transfer_conflict_dialog(parent, files, item, metadata=metadata)
            if dialog is None:
                return

            def poll():
                nonlocal timer
                try:
                    if not dialog.IsModal():
                        return
                    if not current() or not parent_alive():
                        dialog.EndModal(wx.ID_CANCEL)
                        return
                    timer = wx.CallLater(50, poll)
                except RuntimeError:
                    ready.set()

            timer = wx.CallLater(50, poll)
            if dialog.ShowModal() != wx.ID_OK or not current():
                return
            raw = dialog._wx_conflict_result["value"]
            def checked(name):
                control = getattr(dialog, name, None)
                return bool(control and control.GetValue())

            apply_all = checked("_wx_conflict_apply_all")
            always_use = checked("_wx_conflict_always_use")
            downloads_only = checked("_wx_conflict_downloads_only")
            allowed = {
                "overwrite", "overwrite_if_newer", "overwrite_if_size_differs",
                "overwrite_if_size_differs_or_newer", "skip", "resume",
            }
            if not (isinstance(raw, tuple) and len(raw) == 2 and raw[0] == "rename") and raw not in allowed:
                return
            result["value"] = (
                {"value": raw, "apply_all": apply_all, "always_use": always_use,
                 "downloads_only": downloads_only}
                if apply_all or always_use else raw
            )
        except (RuntimeError, AssertionError):
            # Native owner destroyed before the modal interaction completed.
            pass
        finally:
            if timer is not None:
                timer.Stop()
            try:
                if dialog is not None:
                    dialog.Destroy()
            finally:
                ready.set()

    if not current():
        return "cancel"
    try:
        wx.CallAfter(ask)
    except (RuntimeError, AssertionError):
        return "cancel"
    while not ready.wait(0.05):
        if not current():
            return "cancel"
    return result["value"] if current() else "cancel"
