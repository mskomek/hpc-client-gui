"""Native wx remote browser adapter."""

from __future__ import annotations

from threading import Lock, Thread
from pathlib import PurePosixPath

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.services.file_context_actions import FILE_CONTEXT_LABEL_KEYS, context_selection, visible_actions
from hpc_gui.services.file_clipboard import get_file_clipboard
from hpc_gui.services.remote_move_history import RemoteMoveHistory
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel


def show_remote_files(parent=None, model: WxRemoteDirectoryModel | None = None, *, loader=None, operation=None, read_text=None, open_editor=None, open_editor_new_window=None, run_shell=None) -> int:
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    model = model or WxRemoteDirectoryModel()
    frame = wx.Frame(parent, title=t("tabs.ftp"), size=(920, 620))
    panel = wx.Panel(frame)
    root = wx.BoxSizer(wx.VERTICAL)
    notebook = wx.Notebook(panel)
    # path control stays outside notebook to reflect active tab
    path = wx.TextCtrl(panel, value=model.current_path, style=wx.TE_PROCESS_ENTER)
    refresh_btn = wx.Button(panel, label=t("dirs.refresh"))
    root.Add(path, 0, wx.EXPAND | wx.ALL, 6)
    root.Add(notebook, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
    root.Add(refresh_btn, 0, wx.ALIGN_RIGHT | wx.ALL, 6)
    panel.SetSizer(root)
    state = {"closed": False, "editor_request_id": 0, "view_generation": 0, "listing_request_id": 0, "busy": False, "listing_busy": False}
    # state kept for backward compat but per-tab has own
    lock = Lock()
    move_history = RemoteMoveHistory()
    tabs: list[dict] = []
    next_tab_id = [0]

    def safe_call_after(callback, *args):
        try:
            if wx.GetApp() is None:
                return
            wx.CallAfter(callback, *args)
        except BaseException:
            return

    def tab_label(remote_path: str) -> str:
        cleaned = (remote_path or "/").rstrip("/") or "/"
        return cleaned.rsplit("/", 1)[-1] or cleaned

    def active_tab_state():
        sel = notebook.GetSelection()
        if sel < 0 or sel >= len(tabs):
            return tabs[0] if tabs else None
        return tabs[sel]

    def sync_model_active():
        tstate = active_tab_state()
        if not tstate:
            return
        idx = notebook.GetSelection()
        model.active_tab = idx
        if idx < len(model.tabs):
            model.current_path = tstate["path"]
        path.SetValue(tstate["path"])

    def refresh_labels(_language=None):
        frame.SetTitle(t("tabs.ftp"))
        refresh_btn.SetLabel(t("dirs.refresh"))
        for te in tabs:
            try:
                te["listing"].SetColumn(0, t("dirs.col_name"))
                te["listing"].SetColumn(1, t("dirs.col_size"))
            except RuntimeError:
                continue
            idx = tabs.index(te)
            try:
                notebook.SetPageText(idx, tab_label(te["path"]))
            except Exception:
                pass

    def create_tab(remote_path: str):
        remote_path = str(PurePosixPath(remote_path or "/"))
        # normalize
        remote_path = remote_path or "/"
        tab_panel = wx.Panel(notebook)
        listing = wx.ListCtrl(tab_panel, style=wx.LC_REPORT)
        listing.InsertColumn(0, t("dirs.col_name"))
        listing.InsertColumn(1, t("dirs.col_size"))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(listing, 1, wx.EXPAND)
        tab_panel.SetSizer(sizer)
        tab_entry = {"id": next_tab_id[0], "path": remote_path, "listing": listing, "panel": tab_panel, "entries": [], "view_generation": 0, "listing_request_id": 0, "busy": False, "listing_busy": False, "closed": False}
        next_tab_id[0] += 1
        tabs.append(tab_entry)
        listing.Bind(wx.EVT_LIST_ITEM_ACTIVATED, activate)
        listing.Bind(wx.EVT_CONTEXT_MENU, context)
        listing.Bind(wx.EVT_KEY_DOWN, key_down)
        listing.Bind(wx.EVT_MIDDLE_DOWN, middle_click)
        return tab_entry

    def navigate(target):
        tstate = active_tab_state()
        if not tstate:
            return
        tstate_path_before = tstate["path"]
        if str(target) != tstate_path_before:
            state["view_generation"] += 1
            tstate["view_generation"] += 1
        model.navigate(str(target))
        # also update tab's path
        tstate["path"] = model.current_path
        # sync model tabs
        idx = notebook.GetSelection()
        if 0 <= idx < len(model.tabs):
            model.tabs[idx] = model.current_path
        path.SetValue(model.current_path)
        try:
            notebook.SetPageText(idx, tab_label(model.current_path))
        except Exception:
            pass

    def render_for_tab(tab_entry, entries):
        tab_entry["entries"] = list(entries)
        try:
            lst = tab_entry["listing"]
            lst.DeleteAllItems()
            for entry in tab_entry["entries"]:
                idx = lst.InsertItem(lst.GetItemCount(), PurePosixPath(entry.path).name or entry.path)
                lst.SetItem(idx, 1, str(entry.size))
        except RuntimeError:
            return

    def load(_event=None):
        tstate = active_tab_state()
        if not tstate or not loader:
            return
        requested_path_text = path.GetValue().strip()
        if requested_path_text != tstate["path"]:
            try:
                navigate(requested_path_text)
                tstate = active_tab_state()
                requested_path_text = tstate["path"]
            except Exception as error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
                path.SetValue(tstate["path"])
                return
        else:
            # also ensure navigation sync
            requested_path_text = tstate["path"]
        with lock:
            if state["closed"] or tstate.get("closed"):
                return
            state["listing_busy"] = True
            state["listing_request_id"] += 1
            tstate["listing_busy"] = True
            tstate["listing_request_id"] += 1
            tstate["view_generation"] = tstate.get("view_generation", 0)
            request_id = tstate["listing_request_id"]
            request_generation = tstate["view_generation"]
            requested_path = requested_path_text
            tab_id = tstate["id"]

        def done(entries, error):
            with lock:
                tab_entry = next((tt for tt in tabs if tt["id"] == tab_id), None)
                if not tab_entry or tab_entry.get("closed"):
                    return
                current = (
                    not state["closed"]
                    and request_id == tab_entry["listing_request_id"]
                    and request_generation == tab_entry["view_generation"]
                    and requested_path == tab_entry["path"]
                )
                if current:
                    tab_entry["listing_busy"] = False
                    state["listing_busy"] = False
            if not current:
                return
            if error:
                # only show error if this tab is active
                if notebook.GetSelection() == tabs.index(tab_entry):
                    wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            else:
                render_for_tab(tab_entry, entries)

        def worker():
            try:
                safe_call_after(done, model.list_entries(loader, path=requested_path, force=True), None)
            except Exception as error:
                safe_call_after(done, (), error)

        Thread(target=worker, daemon=True).start()

    def activate(event):
        tstate = active_tab_state()
        if not tstate:
            return
        idx = event.GetIndex()
        if idx < 0 or idx >= len(tstate["entries"]):
            return
        entry = tstate["entries"][idx]
        if entry.is_dir:
            navigate(entry.path)
            load()
        elif open_editor:
            open_in_editor(entry.path, open_editor)

    def middle_click(event):
        tstate = active_tab_state()
        if not tstate:
            event.Skip()
            return
        listing = tstate["listing"]
        pos = event.GetPosition()
        idx, _ = listing.HitTest(pos)
        if 0 <= idx < len(tstate["entries"]):
            entry = tstate["entries"][idx]
            if entry.is_dir:
                # open in new visible tab
                model.new_tab(entry.path)
                new_entry = create_tab(entry.path)
                notebook.AddPage(new_entry["panel"], tab_label(entry.path), True)
                # sync after creation
                model.active_tab = notebook.GetSelection()
                model.current_path = entry.path
                path.SetValue(entry.path)
                # update controls for tests
                frame._wx_remote_controls["listing"] = new_entry["listing"]
                frame._wx_remote_controls["path"] = path
                load()
                return
        event.Skip()

    def context(event):
        tstate = active_tab_state()
        if not tstate:
            return
        listing = tstate["listing"]
        entries = tstate["entries"]
        position = event.GetPosition()
        keyboard_context = position == wx.DefaultPosition or (position.x < 0 and position.y < 0)
        index = -1 if keyboard_context else listing.HitTest(listing.ScreenToClient(position))[0]
        if index >= 0 and not listing.IsSelected(index):
            for selected_index in range(listing.GetItemCount()):
                listing.Select(selected_index, False)
            listing.Select(index)
        selected_entries = tuple(entry for idx, entry in enumerate(entries) if listing.IsSelected(idx))
        clicked = entries[index] if 0 <= index < len(entries) else None
        selection = context_selection(
            clicked.path if clicked else None,
            clicked.is_dir if clicked else None,
            tuple(entry.path for entry in selected_entries),
            tuple(entry.is_dir for entry in selected_entries),
            background=index < 0 and not keyboard_context,
        )
        selected = selection.effective_paths
        menu = wx.Menu()
        candidate_actions = ("open", "edit", "edit_new_window", "run_shell", "download", "upload", "copy", "move", "rename", "delete", "paste", "copy_path", "refresh", "new_folder", "new_tab")
        allowed = visible_actions(selection, remote=True)
        actions = tuple(action for action in candidate_actions if action in allowed)
        labels = FILE_CONTEXT_LABEL_KEYS
        for action in actions:
            item = menu.Append(wx.ID_ANY, t(labels.get(action, f"dirs.{action}")))
            target_dir = clicked.path if clicked and clicked.is_dir else tstate["path"]
            listing.Bind(wx.EVT_MENU, lambda _event, action=action, target=target_dir: run_action(action, selected, target), item)
        listing.PopupMenu(menu)
        menu.Destroy()

    def run_action(action, selected, target_dir=None):
        tstate = active_tab_state()
        if not tstate:
            return
        if action == "run_shell" and run_shell and selected:
            run_shell(selected[0])
            return
        if action == "refresh":
            load()
            return
        if action == "new_tab" and selected:
            model.new_tab(selected[0])
            new_entry = create_tab(selected[0])
            notebook.AddPage(new_entry["panel"], tab_label(selected[0]), True)
            model.active_tab = notebook.GetSelection()
            model.current_path = selected[0]
            path.SetValue(model.current_path)
            frame._wx_remote_controls["listing"] = new_entry["listing"]
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
                    # busy per tab?
                    tstate["busy"] = False
                    state["busy"] = False
                if state["closed"] or tstate.get("closed"):
                    return
                try:
                    tstate["listing"].Enable(True)
                except RuntimeError:
                    return
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
                if state["closed"] or tstate.get("closed") or tstate.get("busy") or state.get("busy"):
                    move_history.push(record)
                    return
                state["busy"] = True
                tstate["busy"] = True
            try:
                tstate["listing"].Enable(False)
            except RuntimeError:
                pass
            Thread(target=undo_operation, daemon=True).start()
            return
        if action == "paste":
            clipboard = get_file_clipboard().get()
            if clipboard:
                run_operation(clipboard.op, tuple(clipboard.paths), target_dir or tstate["path"], from_paste=True)
            return
        if action in {"open", "edit"} and open_editor and selected:
            entry = next((item for item in tstate["entries"] if item.path == selected[0]), None)
            if action == "open" and entry and entry.is_dir:
                navigate(selected[0])
                load()
            elif entry and not entry.is_dir:
                open_in_editor(selected[0], open_editor)
        elif action == "edit_new_window" and open_editor_new_window and selected:
            open_in_editor(selected[0], open_editor_new_window)
        else:
            run_operation(action, selected, target_dir or tstate["path"])

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
        tstate = active_tab_state()
        if not tstate:
            return
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
                destination = str(PurePosixPath(target_dir or tstate["path"]) / new_name)
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
            destination = str(PurePosixPath(target_dir or tstate["path"]))
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
                destination = target_dir or tstate["path"]
            finally:
                dialog.Destroy()
        with lock:
            if state["closed"] or tstate.get("closed") or tstate.get("busy") or state.get("busy"):
                return
            state["busy"] = True
            tstate["busy"] = True
            origin_path = tstate["path"]
            origin_generation = tstate["view_generation"]
            tab_id = tstate["id"]
        try:
            tstate["listing"].Enable(False)
        except RuntimeError:
            pass

        def worker():
            try:
                operation(action, operation_paths, destination)
                if action == "move":
                    moved = tuple(
                        (source, str(PurePosixPath(destination) / PurePosixPath(source).name))
                        for source in operation_paths
                    )
                    move_history.record(moved)
                safe_call_after(operation_done, None, tab_id, origin_path, origin_generation)
            except Exception as error:
                safe_call_after(operation_done, error, tab_id, origin_path, origin_generation)

        def operation_done(error, done_tab_id, done_origin_path, done_origin_gen):
            with lock:
                # find tab
                tab_entry = next((tt for tt in tabs if tt["id"] == done_tab_id), None)
                if tab_entry:
                    tab_entry["busy"] = False
                state["busy"] = False
            if state["closed"]:
                return
            if not tab_entry or tab_entry.get("closed"):
                return
            try:
                tab_entry["listing"].Enable(True)
            except RuntimeError:
                return
            if error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            else:
                model.invalidate()
                if tab_entry["path"] == done_origin_path and tab_entry["view_generation"] == done_origin_gen:
                    # if this tab is active, normal load, else targeted load that tab only
                    if notebook.GetSelection() == tabs.index(tab_entry):
                        load()
                    else:
                        # targeted refresh for that tab alone
                        # reuse logic: trigger worker for that tab
                        with lock:
                            if tab_entry.get("closed"):
                                return
                            tab_entry["listing_busy"] = True
                            tab_entry["listing_request_id"] += 1
                            rq_id = tab_entry["listing_request_id"]
                            rq_gen = tab_entry["view_generation"]
                            rq_path = tab_entry["path"]
                            t_id = tab_entry["id"]
                        def done2(entries, err):
                            with lock:
                                te2 = next((tt for tt in tabs if tt["id"] == t_id), None)
                                if not te2 or te2.get("closed") or rq_id != te2["listing_request_id"] or rq_gen != te2["view_generation"] or rq_path != te2["path"]:
                                    te2["listing_busy"] = False if te2 else False
                                    return
                                te2["listing_busy"] = False
                                if err:
                                    return
                                render_for_tab(te2, entries)
                            if err and notebook.GetSelection() == tabs.index(te2):
                                wx.MessageBox(str(err), t("login.err_title"), wx.OK | wx.ICON_ERROR)
                        def wk2():
                            try:
                                safe_call_after(done2, model.list_entries(loader, path=rq_path, force=True) if loader else [], None)
                            except Exception as e2:
                                safe_call_after(done2, (), e2)
                        Thread(target=wk2, daemon=True).start()

        Thread(target=worker, daemon=True).start()

    def close(_event):
        state["closed"] = True
        for te in tabs:
            te["closed"] = True
        frame.Destroy()

    def key_down(event):
        tstate = active_tab_state()
        if not tstate:
            event.Skip()
            return
        listing = tstate["listing"]
        if event.ControlDown() and event.GetKeyCode() == ord("A"):
            for index in range(listing.GetItemCount()):
                listing.Select(index)
            return
        selected = tuple(entry.path for index, entry in enumerate(tstate["entries"]) if listing.IsSelected(index))
        if event.ControlDown() and event.GetKeyCode() in (ord("C"), ord("X"), ord("V")):
            action = {ord("C"): "copy", ord("X"): "cut", ord("V"): "paste"}[event.GetKeyCode()]
            run_action(action, selected, tstate["path"])
            return
        if event.ControlDown() and event.GetKeyCode() == ord("Z"):
            run_action("undo", selected, tstate["path"])
            return
        if event.GetKeyCode() == wx.WXK_BACK:
            navigate(str(PurePosixPath(tstate["path"]).parent))
            load()
            return
        actions = {wx.WXK_F2: "rename", wx.WXK_DELETE: "delete", wx.WXK_F5: "refresh"}
        action = actions.get(event.GetKeyCode())
        if action:
            run_action(action, selected)
            return
        event.Skip()

    def on_page_changed(event):
        new_sel = event.GetSelection()
        if 0 <= new_sel < len(tabs):
            model.active_tab = new_sel
            model.current_path = tabs[new_sel]["path"]
            path.SetValue(tabs[new_sel]["path"])
            if hasattr(frame, "_wx_remote_controls"):
                frame._wx_remote_controls["listing"] = tabs[new_sel]["listing"]
                frame._wx_remote_controls["path"] = path
        event.Skip()

    notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, on_page_changed)
    _orig_set = notebook.SetSelection
    def _patched_set(idx):
        res = _orig_set(idx)
        if 0 <= idx < len(tabs):
            model.active_tab = idx
            model.current_path = tabs[idx]["path"]
            path.SetValue(tabs[idx]["path"])
            if hasattr(frame, "_wx_remote_controls"):
                frame._wx_remote_controls["listing"] = tabs[idx]["listing"]
        return res
    notebook.SetSelection = _patched_set
    _orig_change = notebook.ChangeSelection
    def _patched_change(idx):
        res = _orig_change(idx)
        if 0 <= idx < len(tabs):
            model.active_tab = idx
            model.current_path = tabs[idx]["path"]
            path.SetValue(tabs[idx]["path"])
            if hasattr(frame, "_wx_remote_controls"):
                frame._wx_remote_controls["listing"] = tabs[idx]["listing"]
        return res
    notebook.ChangeSelection = _patched_change

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
        notebook.RemovePage(index)
        try:
            tab_entry["panel"].Destroy()
        except Exception:
            pass
        tabs.pop(index)
        if 0 <= index < len(model.tabs):
            model.tabs.pop(index)
        if active_before == index:
            new_sel = min(index, len(tabs)-1)
            notebook.SetSelection(new_sel)
            model.active_tab = new_sel
            model.current_path = tabs[new_sel]["path"]
            path.SetValue(tabs[new_sel]["path"])
            frame._wx_remote_controls["listing"] = tabs[new_sel]["listing"]
        elif active_before > index:
            model.active_tab = notebook.GetSelection()
            if 0 <= model.active_tab < len(model.tabs):
                model.current_path = tabs[model.active_tab]["path"]
        return True

    def notebook_context(event):
        pos = event.GetPosition()
        if pos == wx.DefaultPosition:
            idx = notebook.GetSelection()
        else:
            try:
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

    notebook.Bind(wx.EVT_CONTEXT_MENU, notebook_context)

    # initial tab
    initial = create_tab(model.current_path)
    notebook.AddPage(initial["panel"], tab_label(model.current_path), True)
    model.active_tab = 0

    refresh_btn.Bind(wx.EVT_BUTTON, load)
    path.Bind(wx.EVT_TEXT_ENTER, load)
    subscribe_language_change(refresh_labels)
    frame.Bind(wx.EVT_CLOSE, lambda event: (unsubscribe_language_change(refresh_labels), close(event)))
    frame._wx_remote_controls = {"listing": initial["listing"], "path": path, "notebook": notebook}
    frame._wx_remote_model = model
    frame._wx_remote_state = state
    frame._wx_remote_run_action = run_action
    frame._wx_remote_tabs = tabs
    frame._wx_remote_notebook = notebook
    frame._wx_remote_close_tab = close_tab
    load()
    frame.Show()
    return wx.ID_OK


__all__ = ["show_remote_files"]
