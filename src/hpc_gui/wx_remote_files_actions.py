"""Private wx remote-file actions component."""

from pathlib import PurePosixPath
from threading import Thread
from hpc_gui.core.i18n import t
from hpc_gui.services.file_clipboard import get_file_clipboard


def install_actions(view):
    _current_navigation_store = view._current_navigation_store
    _show_follow_menu = view._show_follow_menu
    active_tab_state = view.active_tab_state
    chmod = view.chmod
    create_tab = view.create_tab
    host = view.host
    load = view.load
    lock = view.lock
    model = view.model
    move_history = view.move_history
    navigate = view.navigate
    notebook = view.notebook
    open_editor = view.open_editor
    open_editor_new_window = view.open_editor_new_window
    open_in_editor = view.open_in_editor
    operation = view.operation
    path = view.path
    run_direct_operation = view.run_direct_operation
    run_operation = view.run_operation
    run_shell = view.run_shell
    safe_call_after = view.safe_call_after
    state = view.state
    submit_slurm = view.submit_slurm
    tab_label = view.tab_label
    wx = view.wx

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
            host._wx_remote_controls["listing"] = new_entry["listing"]
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
        if action == "follow_track" and selected:
            # Follow/Track: create a submenu with output targets
            _show_follow_menu(selected[0])
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
        if action == "new_file" and operation:
            dlg = wx.TextEntryDialog(host, t("dirs.new_file_label"), t("dirs.new_file_title"))
            if dlg.ShowModal() == wx.ID_OK:
                name = dlg.GetValue().strip()
                if name and "/" not in name and "\\" not in name:
                    try:
                        dest = str(PurePosixPath(tstate["path"]) / name)
                        run_operation("new_file", (), dest)
                        load()
                    except Exception as error:
                        wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            dlg.Destroy()
            return
        if action == "chmod" and selected and callable(chmod):
            dlg = wx.TextEntryDialog(host, t("dirs.permissions_mode"), t("dirs.permissions_title"), "644")
            try:
                if dlg.ShowModal() != wx.ID_OK:
                    return
                mode = dlg.GetValue().strip()
                if len(mode) not in (3, 4) or any(char not in "01234567" for char in mode):
                    wx.MessageBox(t("dirs.permissions_invalid"), t("dirs.permissions_title"), wx.OK | wx.ICON_ERROR)
                    return
                run_direct_operation(lambda: chmod(selected[0], int(mode, 8)))
            finally:
                dlg.Destroy()
            return
        if action == "submit_slurm" and selected and callable(submit_slurm):
            run_direct_operation(lambda: submit_slurm(selected[0]))
            return
        if action == "favorite" and _current_navigation_store() and tstate:
            try:
                entry = next((item for item in tstate["entries"] if item.path in selected), None)
                target = entry.path if entry else tstate["path"]
                kind = "file" if entry is not None and not entry.is_dir else "directory"
                _current_navigation_store().toggle_favorite(target, kind)
            except Exception:
                pass
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

    view.run_action = run_action
