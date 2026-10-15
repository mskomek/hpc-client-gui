"""Private wx local-file lifecycle component."""

from hpc_gui.core.i18n import t, unsubscribe_language_change

def install_lifecycle(view):
    _orig_change = view._orig_change
    _orig_set = view._orig_set
    active_tab_state = view.active_tab_state
    host = view.host
    model = view.model
    navigate = view.navigate
    notebook = view.notebook
    path_ctrl = view.path_ctrl
    refresh = view.refresh
    refresh_labels = view.refresh_labels
    state = view.state
    tabs = view.tabs
    wx = view.wx

    def on_page_changed(event):
        # update model to reflect new active tab
        new_sel = event.GetSelection()
        if 0 <= new_sel < len(tabs):
            model.active_tab = new_sel
            model.current_path = tabs[new_sel]["path"]
            try:
                path_ctrl.SetValue(str(tabs[new_sel]["path"]))
            except Exception:
                pass
            # update global controls reference for tests (guard before attribute exists)
            if hasattr(host, "_wx_local_controls"):
                host._wx_local_controls["listing"] = tabs[new_sel]["listing"]
                host._wx_local_controls["path"] = path_ctrl
        event.Skip()

    def _patched_set(idx):
        res = _orig_set(idx)
        if 0 <= idx < len(tabs):
            model.active_tab = idx
            model.current_path = tabs[idx]["path"]
            try:
                path_ctrl.SetValue(str(tabs[idx]["path"]))
            except Exception:
                pass
            if hasattr(host, "_wx_local_controls"):
                host._wx_local_controls["listing"] = tabs[idx]["listing"]
                host._wx_local_controls["path"] = path_ctrl
        return res

    def _patched_change(idx):
        res = _orig_change(idx)
        if 0 <= idx < len(tabs):
            model.active_tab = idx
            model.current_path = tabs[idx]["path"]
            try:
                path_ctrl.SetValue(str(tabs[idx]["path"]))
            except Exception:
                pass
            if hasattr(host, "_wx_local_controls"):
                host._wx_local_controls["listing"] = tabs[idx]["listing"]
                host._wx_local_controls["path"] = path_ctrl
        return res

    def close_tab(index: int | None = None):
        if len(tabs) <= 1:
            return False
        if index is None:
            index = notebook.GetSelection()
        if not (0 <= index < len(tabs)):
            return False
        active_before = notebook.GetSelection()
        tab_entry = tabs[index]
        tab_entry["closed"] = True
        # remove page
        notebook.RemovePage(index)
        # destroy panel to mimic real close but keep listing object flag?
        try:
            tab_entry["panel"].Destroy()
        except Exception:
            pass
        tabs.pop(index)
        model.tabs.pop(index)
        # adjust active
        if active_before == index:
            new_sel = min(index, len(tabs)-1)
            notebook.SetSelection(new_sel)
            model.active_tab = new_sel
            model.current_path = tabs[new_sel]["path"]
            host._wx_local_controls["listing"] = tabs[new_sel]["listing"]
            try:
                path_ctrl.SetValue(str(tabs[new_sel]["path"]))
            except Exception:
                pass
        elif active_before > index:
            # active shifted left
            model.active_tab = notebook.GetSelection()
            if 0 <= model.active_tab < len(model.tabs):
                model.current_path = tabs[model.active_tab]["path"]
                try:
                    path_ctrl.SetValue(str(tabs[model.active_tab]["path"]))
                except Exception:
                    pass
        else:
            # active unchanged
            pass
        # Clamp
        if model.active_tab >= len(model.tabs):
            model.active_tab = len(model.tabs)-1
        return True

    def notebook_context(event):
        pos = event.GetPosition()
        if pos == wx.DefaultPosition:
            idx = notebook.GetSelection()
        else:
            try:
                # HitTest returns (idx, flags)
                hit = notebook.HitTest(notebook.ScreenToClient(pos))
                idx = hit[0] if isinstance(hit, tuple) else hit
            except Exception:
                idx = notebook.GetSelection()
        if idx < 0 or idx >= notebook.GetPageCount():
            return
        menu = wx.Menu()
        close_item = menu.Append(wx.ID_ANY, t("common.close"))
        close_item.Enable(notebook.GetPageCount() > 1)
        def do_close(_evt, target=idx):
            close_tab(target)
        notebook.Bind(wx.EVT_MENU, do_close, close_item)
        notebook.PopupMenu(menu)
        menu.Destroy()

    def _on_path_enter(event):
        text = path_ctrl.GetValue().strip()
        if not text:
            try:
                path_ctrl.SetValue(str(active_tab_state()["path"]))
            except Exception:
                pass
            return
        try:
            navigate(text)
            refresh()
        except Exception as error:
            wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            try:
                path_ctrl.SetValue(str(active_tab_state()["path"]))
            except Exception:
                pass

    def close(event):
        state["closed"] = True
        for te in tabs:
            te["closed"] = True
        unsubscribe_language_change(refresh_labels)
        event.Skip()

    view.on_page_changed = on_page_changed
    view._patched_set = _patched_set
    view._patched_change = _patched_change
    view.close_tab = close_tab
    view.notebook_context = notebook_context
    view._on_path_enter = _on_path_enter
    view.close = close
