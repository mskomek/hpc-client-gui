"""Private wx local-file mutations component."""

from threading import Thread
from hpc_gui.core.i18n import t
from hpc_gui.wx_local_files_model import open_with_system, reveal_in_file_manager

def install_mutations(view):
    active_tab_state = view.active_tab_state
    confirm_local_delete = view.confirm_local_delete
    create_tab = view.create_tab
    host = view.host
    model = view.model
    navigate = view.navigate
    notebook = view.notebook
    open_editor = view.open_editor
    open_editor_new_window = view.open_editor_new_window
    path_ctrl = view.path_ctrl
    refresh = view.refresh
    render_entries = view.render_entries
    run_shell = view.run_shell
    safe_call_after = view.safe_call_after
    selected_entries = view.selected_entries
    state = view.state
    tab_label = view.tab_label
    tabs = view.tabs
    threading_lock = view.threading_lock
    upload = view.upload
    wx = view.wx

    def mutate(operation, *, selection_after=()) -> None:
        tstate = active_tab_state()
        if not tstate:
            return
        if state["closed"] or state["mutation_in_flight"] or tstate.get("closed"):
            return
        state["mutation_in_flight"] = True
        listing = tstate["listing"]
        listing.Enable(False)
        origin_path = tstate["path"]
        origin_generation = tstate["view_generation"]
        tab_id = tstate["id"]

        def worker():
            try:
                operation()
                safe_call_after(mutation_done, None, tab_id, origin_path, origin_generation)
            except Exception as error:
                safe_call_after(mutation_done, error, tab_id, origin_path, origin_generation)

        def mutation_done(error, done_tab_id, done_origin_path, done_origin_gen):
            state["mutation_in_flight"] = False
            if state["closed"]:
                return
            tab_entry = next((tt for tt in tabs if tt["id"] == done_tab_id), None)
            if not tab_entry or tab_entry.get("closed"):
                return
            try:
                tab_entry["listing"].Enable(True)
            except RuntimeError:
                return
            if error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            elif tab_entry["path"] == done_origin_path and tab_entry["view_generation"] == done_origin_gen:
                # need to refresh that specific tab; temporarily make it active concept? just refresh logic for that tab directly
                # if that tab is active, use normal refresh; else do targeted refresh
                if notebook.GetSelection() == tabs.index(tab_entry):
                    refresh(selection_after)
                else:
                    # targeted refresh for non-active tab
                    # we could directly call refresh for that tab entry
                    # simulate refresh but scoped to that tab
                    with threading_lock:
                        if tab_entry.get("closed"):
                            return
                        tab_entry["listing_request_id"] += 1
                        tab_entry["view_generation"] += 1
                        req_id = tab_entry["listing_request_id"]
                        req_gen = tab_entry["view_generation"]
                        req_path = tab_entry["path"]
                        tid = tab_entry["id"]
                    def done2(result, err):
                        with threading_lock:
                            te = next((tt for tt in tabs if tt["id"] == tid), None)
                            if not te or te.get("closed") or req_id != te["listing_request_id"] or req_gen != te["view_generation"] or req_path != te["path"]:
                                return
                        if err:
                            return
                        render_entries(te, result, selection_after)
                    def wk2():
                        try:
                            safe_call_after(done2, model.list_entries(req_path), None)
                        except Exception as e2:
                            safe_call_after(done2, (), e2)
                    Thread(target=wk2, daemon=True).start()

        Thread(target=worker, daemon=True).start()

    def run_action(action: str) -> None:
        tstate = active_tab_state()
        if not tstate:
            return
        selected = selected_entries()
        if action == "run_shell" and run_shell and selected:
            run_shell(str(selected[0].path))
            return
        if action == "upload" and upload:
            if selected:
                upload(tuple(str(item.path) for item in selected))
            else:
                dialog = wx.FileDialog(host, t("ftp.upload_selected"), style=wx.FD_OPEN | wx.FD_MULTIPLE)
                try:
                    if dialog.ShowModal() == wx.ID_OK:
                        upload(tuple(dialog.GetPaths()))
                finally:
                    dialog.Destroy()
            return
        if action == "new_folder":
            dialog = wx.TextEntryDialog(host, t("dirs.new_folder"), t("dirs.new_folder"))
            try:
                if dialog.ShowModal() == wx.ID_OK:
                    name = dialog.GetValue()
                    target = state["context_target"] or (selected[0].path if len(selected) == 1 and selected[0].is_dir else tstate["path"])
                    mutate(lambda: model.new_folder(name, target))
            except Exception as error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            finally:
                dialog.Destroy()
            return
        if action == "paste":
            # snapshot destination and clipboard at action time
            dest_snapshot = tstate["path"]
            clip_snapshot = tuple(model.clipboard)
            move_snapshot = model.clipboard_move
            mutate(lambda: model.paste_into(dest_snapshot, clip_snapshot, move_snapshot))
            return
        if action == "refresh":
            refresh()
            return
        if not selected:
            return
        entry = selected[0]
        if action in {"copy", "cut"}:
            model.copy([item.path for item in selected], move=action == "cut")
            return
        if action in {"open", "edit", "edit_new_window", "new_tab"}:
            if action == "new_tab":
                # create visible second tab
                model.new_tab(entry.path)
                new_entry = create_tab(entry.path)
                notebook.AddPage(new_entry["panel"], tab_label(entry.path), True)
                model.active_tab = notebook.GetSelection()
                model.current_path = entry.path
                try:
                    path_ctrl.SetValue(str(entry.path))
                except Exception:
                    pass
                if hasattr(host, "_wx_local_controls"):
                    host._wx_local_controls["listing"] = new_entry["listing"]
                # keep state view_generation in sync
                # refresh will handle
                refresh()
            elif action == "open":
                if entry.is_dir:
                    navigate(entry.path)
                    refresh()
                else:
                    try:
                        reveal_in_file_manager(entry.path)
                    except OSError as error:
                        wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            elif action == "edit_new_window" and open_editor_new_window:
                open_editor_new_window(str(entry.path))
            else:
                if open_editor:
                    for item in selected:
                        open_editor(str(item.path))
        elif action == "open_with":
            try:
                open_with_system(entry.path)
            except OSError as error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
        elif action == "copy_path":
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(str(entry.path)))
                wx.TheClipboard.Close()
        elif action == "rename":
            dialog = wx.TextEntryDialog(host, t("dirs.rename"), t("dirs.rename"), entry.path.name)
            try:
                if dialog.ShowModal() == wx.ID_OK:
                    new_name = dialog.GetValue()
                    origin_snapshot = tstate["path"]
                    src_snapshot = entry.path
                    selected_after = tuple(
                        src_snapshot.with_name(new_name) if item.path == src_snapshot else item.path
                        for item in selected
                    )
                    mutate(
                        lambda: model.rename_at(src_snapshot, new_name, origin_snapshot),
                        selection_after=selected_after,
                    )
            except Exception as error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            finally:
                dialog.Destroy()
        elif action == "delete" and confirm_local_delete(
            [item.path.name for item in selected], str(tstate["path"])
        ):
            paths = tuple(item.path for item in selected)
            origin_snapshot = tstate["path"]
            mutate(lambda: model.delete_at(list(paths), origin_snapshot))

    view.mutate = mutate
    view.run_action = run_action
