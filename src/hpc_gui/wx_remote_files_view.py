"""Native wx remote browser adapter."""

from __future__ import annotations

from threading import Lock, Thread
from pathlib import PurePosixPath

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.services.file_context_actions import FILE_CONTEXT_LABEL_KEYS, context_selection, visible_actions
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel


def show_remote_files(parent=None, model: WxRemoteDirectoryModel | None = None, *, loader=None, operation=None, read_text=None, open_editor=None, open_editor_new_window=None) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    model = model or WxRemoteDirectoryModel()
    frame = wx.Frame(parent, title=t("tabs.ftp"), size=(920, 620))
    panel = wx.Panel(frame)
    root = wx.BoxSizer(wx.VERTICAL)
    path = wx.TextCtrl(panel, value=model.current_path, style=wx.TE_PROCESS_ENTER)
    listing = wx.ListCtrl(panel, style=wx.LC_REPORT)
    listing.InsertColumn(0, t("dirs.col_name"))
    listing.InsertColumn(1, t("dirs.col_size"))
    refresh = wx.Button(panel, label=t("dirs.refresh"))
    root.Add(path, 0, wx.EXPAND | wx.ALL, 6)
    root.Add(listing, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
    root.Add(refresh, 0, wx.ALIGN_RIGHT | wx.ALL, 6)
    panel.SetSizer(root)
    state = {"entries": [], "busy": False, "closed": False, "editor_request_id": 0}
    lock = Lock()

    def render(entries):
        state["entries"] = list(entries)
        listing.DeleteAllItems()
        for entry in state["entries"]:
            index = listing.InsertItem(listing.GetItemCount(), PurePosixPath(entry.path).name or entry.path)
            listing.SetItem(index, 1, str(entry.size))

    def refresh_labels(_language=None):
        frame.SetTitle(t("tabs.ftp"))
        listing.SetColumn(0, t("dirs.col_name"))
        listing.SetColumn(1, t("dirs.col_size"))
        refresh.SetLabel(t("dirs.refresh"))

    def load(_event=None):
        if not loader:
            return
        requested_path = path.GetValue().strip()
        if requested_path != model.current_path:
            try:
                model.navigate(requested_path)
            except Exception as error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
                path.SetValue(model.current_path)
                return
        with lock:
            if state["closed"] or state["busy"]:
                return
            state["busy"] = True

        def done(entries, error):
            with lock:
                state["busy"] = False
            if state["closed"]:
                return
            if error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            else:
                render(entries)

        def worker():
            try:
                wx.CallAfter(done, model.list_entries(loader, force=True), None)
            except Exception as error:
                wx.CallAfter(done, (), error)

        Thread(target=worker, daemon=True).start()

    def activate(event):
        entry = state["entries"][event.GetIndex()]
        if entry.is_dir:
            model.navigate(entry.path)
            path.SetValue(model.current_path)
            load()
        elif open_editor:
            open_in_editor(entry.path, open_editor)

    def context(event):
        position = event.GetPosition()
        index = -1 if position == wx.DefaultPosition else listing.HitTest(listing.ScreenToClient(position))[0]
        if index >= 0 and not listing.IsSelected(index):
            for selected_index in range(listing.GetItemCount()):
                listing.Select(selected_index, False)
            listing.Select(index)
        selected_entries = tuple(entry for idx, entry in enumerate(state["entries"]) if listing.IsSelected(idx))
        clicked = state["entries"][index] if index >= 0 else None
        selection = context_selection(
            clicked.path if clicked else None,
            clicked.is_dir if clicked else None,
            tuple(entry.path for entry in selected_entries),
            tuple(entry.is_dir for entry in selected_entries),
            background=index < 0 and position != wx.DefaultPosition,
        )
        selected = selection.effective_paths
        menu = wx.Menu()
        candidate_actions = ("open", "edit", "edit_new_window", "download", "upload", "copy", "move", "rename", "delete", "paste", "copy_path", "refresh", "new_folder", "new_tab")
        allowed = visible_actions(selection, remote=True)
        actions = tuple(action for action in candidate_actions if action in allowed)
        labels = FILE_CONTEXT_LABEL_KEYS
        for action in actions:
            item = menu.Append(wx.ID_ANY, t(labels.get(action, f"dirs.{action}")))
            target_dir = clicked.path if clicked and clicked.is_dir else model.current_path
            listing.Bind(wx.EVT_MENU, lambda _event, action=action, target=target_dir: run_action(action, selected, target), item)
        listing.PopupMenu(menu)
        menu.Destroy()

    def run_action(action, selected, target_dir=None):
        if action == "refresh":
            load()
            return
        if action == "new_tab" and selected:
            model.new_tab(selected[0])
            path.SetValue(model.current_path)
            load()
            return
        if action in {"open", "edit"} and open_editor and selected:
            entry = next((item for item in state["entries"] if item.path == selected[0]), None)
            if action == "open" and entry and entry.is_dir:
                model.navigate(selected[0])
                path.SetValue(model.current_path)
                load()
            elif entry and not entry.is_dir:
                open_in_editor(selected[0], open_editor)
        elif action == "edit_new_window" and open_editor_new_window and selected:
            open_in_editor(selected[0], open_editor_new_window)
        else:
            run_operation(action, selected, target_dir or model.current_path)

    def open_in_editor(remote_path, callback):
        if not read_text:
            callback(remote_path)
            return
        with lock:
            if state["closed"]:
                return
            state["editor_request_id"] += 1
            request_id = callback._wx_request_started() if getattr(callback, "_wx_request_started", None) else state["editor_request_id"]

        def done(content, error):
            if state["closed"]:
                return
            if error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            else:
                if getattr(callback, "_wx_request_aware", False):
                    callback(remote_path, content, request_id)
                else:
                    callback(remote_path, content)

        def worker():
            try:
                wx.CallAfter(done, read_text(remote_path), None)
            except Exception as error:
                wx.CallAfter(done, "", error)

        Thread(target=worker, daemon=True).start()

    def run_operation(action, selected, target_dir=None):
        if not operation or action in {"open", "edit", "edit_new_window"} or (not selected and action not in {"new_folder", "upload"}):
            return
        if action == "delete" and wx.MessageBox(t("dirs.delete_confirm"), t("dirs.delete"), wx.YES_NO | wx.ICON_WARNING) != wx.YES:
            return
        destination = ""
        operation_paths = selected
        if action == "new_folder":
            dialog = wx.TextEntryDialog(frame, t("dirs.new_folder"), t("dirs.new_folder"))
            try:
                if dialog.ShowModal() != wx.ID_OK:
                    return
                new_name = dialog.GetValue().strip()
                if not new_name or PurePosixPath(new_name).name != new_name or new_name in {".", ".."}:
                    wx.MessageBox(t("dirs.rename_invalid"), t("dirs.new_folder"), wx.OK | wx.ICON_ERROR)
                    return
                destination = str(PurePosixPath(target_dir or model.current_path) / new_name)
            finally:
                dialog.Destroy()
        elif action in {"rename", "copy", "move"}:
            title_key = "dirs.rename" if action == "rename" else "dirs.destination"
            default = PurePosixPath(selected[0]).name if action == "rename" else str(PurePosixPath(selected[0]).parent)
            dialog = wx.TextEntryDialog(frame, t(title_key), t(title_key), default)
            try:
                if dialog.ShowModal() != wx.ID_OK:
                    return
                new_name = dialog.GetValue().strip()
                if not new_name or (action == "rename" and (PurePosixPath(new_name).name != new_name or new_name in {".", ".."})):
                    wx.MessageBox(t("dirs.rename_invalid"), t("dirs.rename"), wx.OK | wx.ICON_ERROR)
                    return
                destination = str(PurePosixPath(selected[0]).parent / new_name) if action == "rename" else str(PurePosixPath(new_name))
            finally:
                dialog.Destroy()
        elif action == "download":
            dialog = wx.DirDialog(frame, t("dirs.local_destination"))
            try:
                if dialog.ShowModal() != wx.ID_OK:
                    return
                destination = dialog.GetPath()
            finally:
                dialog.Destroy()
        elif action == "upload":
            dialog = wx.FileDialog(frame, t("ftp.upload_selected"), style=wx.FD_OPEN | wx.FD_MULTIPLE)
            try:
                if dialog.ShowModal() != wx.ID_OK:
                    return
                operation_paths = tuple(dialog.GetPaths())
                destination = target_dir or model.current_path
            finally:
                dialog.Destroy()
        with lock:
            if state["closed"] or state["busy"]:
                return
            state["busy"] = True
        listing.Enable(False)

        def worker():
            try:
                operation(action, operation_paths, destination)
                wx.CallAfter(operation_done, None)
            except Exception as error:
                wx.CallAfter(operation_done, error)

        def operation_done(error):
            with lock:
                state["busy"] = False
            if state["closed"]:
                return
            listing.Enable(True)
            if error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            else:
                model.invalidate()
                load()

        Thread(target=worker, daemon=True).start()

    def close(_event):
        state["closed"] = True
        frame.Destroy()

    def key_down(event):
        if event.ControlDown() and event.GetKeyCode() == ord("A"):
            for index in range(listing.GetItemCount()):
                listing.Select(index)
            return
        if event.GetKeyCode() == wx.WXK_BACK:
            model.navigate(str(PurePosixPath(model.current_path).parent))
            path.SetValue(model.current_path)
            load()
            return
        actions = {wx.WXK_F2: "rename", wx.WXK_DELETE: "delete", wx.WXK_F5: "refresh"}
        action = actions.get(event.GetKeyCode())
        if action:
            selected = tuple(entry.path for index, entry in enumerate(state["entries"]) if listing.IsSelected(index))
            run_action(action, selected)
            return
        event.Skip()

    listing.Bind(wx.EVT_LIST_ITEM_ACTIVATED, activate)
    listing.Bind(wx.EVT_CONTEXT_MENU, context)
    listing.Bind(wx.EVT_KEY_DOWN, key_down)
    refresh.Bind(wx.EVT_BUTTON, load)
    path.Bind(wx.EVT_TEXT_ENTER, load)
    subscribe_language_change(refresh_labels)
    frame.Bind(wx.EVT_CLOSE, lambda event: (unsubscribe_language_change(refresh_labels), close(event)))
    frame._wx_remote_controls = {"listing": listing, "path": path}
    frame._wx_remote_state = state
    frame._wx_remote_run_action = run_action
    load()
    frame.Show()
    return wx.ID_OK


__all__ = ["show_remote_files"]
