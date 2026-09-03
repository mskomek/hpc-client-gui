"""Native wx remote browser adapter."""

from __future__ import annotations

from threading import Lock, Thread
from pathlib import PurePosixPath

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.services.file_context_actions import FILE_CONTEXT_LABEL_KEYS, context_selection, visible_actions
from hpc_gui.services.file_clipboard import get_file_clipboard
from hpc_gui.services.remote_move_history import RemoteMoveHistory
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
    state = {"entries": [], "busy": False, "listing_busy": False, "closed": False, "editor_request_id": 0, "view_generation": 0, "listing_request_id": 0}
    lock = Lock()
    move_history = RemoteMoveHistory()

    def safe_call_after(callback, *args):
        try:
            wx.CallAfter(callback, *args)
        except (AssertionError, RuntimeError):
            # The wx application may have been destroyed while a worker exits.
            return

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

    def navigate(target):
        if str(target) != model.current_path:
            state["view_generation"] += 1
        model.navigate(str(target))
        path.SetValue(model.current_path)

    def load(_event=None):
        if not loader:
            return
        requested_path = path.GetValue().strip()
        if requested_path != model.current_path:
            try:
                navigate(requested_path)
            except Exception as error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
                path.SetValue(model.current_path)
                return
        with lock:
            if state["closed"]:
                return
            state["listing_busy"] = True
            state["listing_request_id"] += 1
            request_id = state["listing_request_id"]
            request_generation = state["view_generation"]

        def done(entries, error):
            with lock:
                current = (
                    not state["closed"]
                    and request_id == state["listing_request_id"]
                    and request_generation == state["view_generation"]
                    and requested_path == model.current_path
                )
                if current:
                    state["listing_busy"] = False
            if not current:
                return
            if error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            else:
                render(entries)

        def worker():
            try:
                safe_call_after(done, model.list_entries(loader, force=True), None)
            except Exception as error:
                safe_call_after(done, (), error)

        Thread(target=worker, daemon=True).start()

    def activate(event):
        entry = state["entries"][event.GetIndex()]
        if entry.is_dir:
            navigate(entry.path)
            load()
        elif open_editor:
            open_in_editor(entry.path, open_editor)

    def context(event):
        position = event.GetPosition()
        keyboard_context = position == wx.DefaultPosition or (position.x < 0 and position.y < 0)
        index = -1 if keyboard_context else listing.HitTest(listing.ScreenToClient(position))[0]
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
            background=index < 0 and not keyboard_context,
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
        if action in {"copy", "cut"} and selected:
            get_file_clipboard().set("move" if action == "cut" else "copy", list(selected))
            return
        if action == "copy_path" and selected:
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject("\r\n".join(selected)))
                wx.TheClipboard.Close()
            return
        if action == "undo":
            record = move_history.pop_last()
            if not record:
                return
            inverse = tuple((moved, original) for original, moved in record.moves)
            def undo_done(error):
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
            def undo_operation():
                completed = 0
                try:
                    for source, destination in inverse:
                        operation("move", (source,), destination.rsplit("/", 1)[0] or "/")
                        completed += 1
                    safe_call_after(undo_done, None)
                except Exception as error:
                    if completed < len(record.moves):
                        move_history.push(type(record)(record.moves[completed:]))
                    safe_call_after(undo_done, error)
            with lock:
                if state["closed"] or state["busy"]:
                    move_history.push(record)
                    return
                state["busy"] = True
            listing.Enable(False)
            Thread(target=undo_operation, daemon=True).start()
            return
        if action == "paste":
            clipboard = get_file_clipboard().get()
            if clipboard:
                run_operation(clipboard.op, tuple(clipboard.paths), target_dir or model.current_path, from_paste=True)
            return
        if action in {"open", "edit"} and open_editor and selected:
            entry = next((item for item in state["entries"] if item.path == selected[0]), None)
            if action == "open" and entry and entry.is_dir:
                navigate(selected[0])
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
                safe_call_after(done, read_text(remote_path), None)
            except Exception as error:
                safe_call_after(done, "", error)

        Thread(target=worker, daemon=True).start()

    def run_operation(action, selected, target_dir=None, *, from_paste=False):
        if not operation or action in {"open", "edit", "edit_new_window"} or (not selected and action not in {"new_folder", "upload", "paste"}):
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
        elif action in {"rename", "copy", "move"} and not from_paste:
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
        elif from_paste:
            destination = str(PurePosixPath(target_dir or model.current_path))
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
            origin_path = model.current_path
            origin_generation = state["view_generation"]
        listing.Enable(False)

        def worker():
            try:
                operation(action, operation_paths, destination)
                if action == "move":
                    moved = tuple(
                        (source, str(PurePosixPath(destination) / PurePosixPath(source).name))
                        for source in operation_paths
                    )
                    move_history.record(moved)
                safe_call_after(operation_done, None)
            except Exception as error:
                safe_call_after(operation_done, error)

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
                if model.current_path == origin_path and state["view_generation"] == origin_generation:
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
        selected = tuple(entry.path for index, entry in enumerate(state["entries"]) if listing.IsSelected(index))
        if event.ControlDown() and event.GetKeyCode() in (ord("C"), ord("X"), ord("V")):
            action = {ord("C"): "copy", ord("X"): "cut", ord("V"): "paste"}[event.GetKeyCode()]
            run_action(action, selected, model.current_path)
            return
        if event.ControlDown() and event.GetKeyCode() == ord("Z"):
            run_action("undo", selected, model.current_path)
            return
        if event.GetKeyCode() == wx.WXK_BACK:
            navigate(str(PurePosixPath(model.current_path).parent))
            load()
            return
        actions = {wx.WXK_F2: "rename", wx.WXK_DELETE: "delete", wx.WXK_F5: "refresh"}
        action = actions.get(event.GetKeyCode())
        if action:
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
    frame._wx_remote_model = model
    frame._wx_remote_state = state
    frame._wx_remote_run_action = run_action
    load()
    frame.Show()
    return wx.ID_OK


__all__ = ["show_remote_files"]
