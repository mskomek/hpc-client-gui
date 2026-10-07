"""Frame-owned transient window tracking and shell menu handlers."""
from __future__ import annotations

from hpc_gui.core.i18n import current_language, set_language, t
from hpc_gui.wx_shell_dispatch import _dispatch
from hpc_gui.wx_shell_settings import run_wx_update_check


def create_window_event_state(wx, frame, lifecycle, session_state):
    # --- chrome parenting / tracking (Part 3) ---
    chrome_windows: list = []
    shell_ref = [frame]

    def _shell_frame():
        f = shell_ref[0] if shell_ref else None
        if f is None:
            return None
        try:
            if not wx.Window.FindWindowById(f.GetId()):
                return None
        except Exception:
            return None
        # also check if being deleted
        try:
            if f.IsBeingDeleted():
                return None
        except Exception:
            pass
        return f

    def _track_new_windows(before_set):
        f = _shell_frame()
        if f is None:
            return
        after = set(wx.GetTopLevelWindows())
        for w in after - before_set:
            try:
                if w.GetParent() is f:
                    chrome_windows.append(w)
                    # untrack when child closes/destroys
                    def _on_child_close(evt, win=w):
                        try:
                            if win in chrome_windows:
                                chrome_windows.remove(win)
                        except Exception:
                            pass
                        evt.Skip()
                    def _on_child_destroy(evt, win=w):
                        try:
                            if win in chrome_windows:
                                chrome_windows.remove(win)
                        except Exception:
                            pass
                        evt.Skip()
                    w.Bind(wx.EVT_CLOSE, _on_child_close)
                    w.Bind(wx.EVT_WINDOW_DESTROY, _on_child_destroy)
            except Exception:
                pass

    def _on_help(_event):
        f = _shell_frame()
        if not f:
            return
        _dispatch("APP-HELP", f, lifecycle, session_state)

    def _on_update(_event):
        # W41 UPDATER-ROUTE-002: delegate to the single authoritative
        # update-check controller; no divergent second route.
        f = _shell_frame()
        if not f:
            return
        try:
            run_wx_update_check(f)
        except Exception:
            return
        try:
            _track_new_windows(set(wx.GetTopLevelWindows()))
        except Exception:
            pass

    def _on_plugins(_event):
        f = _shell_frame()
        if not f:
            return
        before = set(wx.GetTopLevelWindows())
        # W02 ERROR-GOV: route through _dispatch like _on_help so failures
        # are visible with a stable code instead of silently swallowed.
        _dispatch("PLUGIN-BROWSE", f, lifecycle, session_state)
        _track_new_windows(before)

    def _on_send_logs(_event):
        f = _shell_frame()
        if not f:
            return
        before = set(wx.GetTopLevelWindows())
        # W02 ERROR-GOV: route through _dispatch like _on_help so failures
        # are visible with a stable code instead of silently swallowed.
        _dispatch("APP-SEND-LOGS", f, lifecycle, session_state)
        _track_new_windows(before)

    def _on_settings(_event):
        f = _shell_frame()
        if not f:
            return
        before = set(wx.GetTopLevelWindows())
        # W02 ERROR-GOV: route through _dispatch like _on_help so failures
        # are visible with a stable code instead of silently swallowed.
        _dispatch("APP-SETTINGS", f, lifecycle, session_state)
        _track_new_windows(before)

    def _on_language_button(_event):
        f = _shell_frame()
        if not f:
            return
        # show popup menu parented to shell frame, not button
        cur = current_language()
        menu = wx.Menu()
        ids = {}
        for lang, key in (("en", "english"), ("tr", "turkish")):
            item = menu.AppendRadioItem(wx.ID_ANY, t(f"language.{key}"))
            try:
                item.SetBitmap(_flag_bitmap(wx, lang))
            except Exception:
                pass
            if lang == cur:
                item.Check(True)
            ids[item.GetId()] = lang

        def on_choice(evt):
            lang = ids.get(evt.GetId())
            if lang:
                set_language(lang)

        # bind each id
        for _id in ids:
            f.Bind(wx.EVT_MENU, on_choice, id=_id)
        try:
            f.PopupMenu(menu)
        finally:
            menu.Destroy()
            for _id in ids:
                try:
                    f.Unbind(wx.EVT_MENU, id=_id)
                except Exception:
                    pass


    return chrome_windows, shell_ref
