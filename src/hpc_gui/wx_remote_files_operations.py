"""Private wx remote-file operations component."""

from pathlib import PurePosixPath
from threading import Thread
from hpc_gui.core.i18n import t
from hpc_gui.wx_remote_files_support import _entry_name


def install_operations(view):
    active_tab_state = view.active_tab_state
    confirm_remote_delete = view.confirm_remote_delete
    host = view.host
    load = view.load
    loader = view.loader
    lock = view.lock
    model = view.model
    move_history = view.move_history
    notebook = view.notebook
    operation = view.operation
    panel = view.panel
    read_text = view.read_text
    render_for_tab = view.render_for_tab
    safe_call_after = view.safe_call_after
    state = view.state
    tabs = view.tabs
    wx = view.wx

    def run_direct_operation(callback):
        """Run a safe application-owned file action off the GUI thread."""
        with lock:
            if state["closed"]:
                return
            state["busy"] = True
        def worker():
            try:
                result = callback()
                safe_call_after(direct_done, None, result)
            except Exception as error:
                safe_call_after(direct_done, error, None)
        def direct_done(error, result):
            state["busy"] = False
            if state["closed"]:
                return
            if error:
                wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            else:
                model.invalidate()
                load()
                if result is not None:
                    wx.MessageBox(str(result), t("common.info"), wx.OK | wx.ICON_INFORMATION)
        Thread(target=worker, daemon=True).start()

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

    def _show_follow_menu(remote_path):
        """Show a Follow/Track submenu for the selected file."""
        menu = wx.Menu()
        # Check if file is already being followed
        already_following = _is_file_followed(remote_path)
        if already_following:
            menu.Append(wx.ID_ANY, t("dirs.following") + " ✓").Enable(False)
            menu.AppendSeparator()
        item_new_tab = menu.Append(wx.ID_ANY, t("dirs.follow_new_tab"))
        item_new_window = menu.Append(wx.ID_ANY, t("dirs.follow_new_window"))
        menu.Bind(wx.EVT_MENU, lambda e: _follow_in_new_tab(remote_path), id=item_new_tab.GetId())
        menu.Bind(wx.EVT_MENU, lambda e: _follow_in_new_window(remote_path), id=item_new_window.GetId())
        # "Assign to Existing Follower" submenu
        existing_followers = _get_existing_followers()
        if existing_followers:
            menu.AppendSeparator()
            sub = wx.Menu()
            for fid, flabel in existing_followers:
                item = sub.Append(wx.ID_ANY, flabel)
                menu.Bind(wx.EVT_MENU, lambda e, fp=remote_path, fi=fid: _follow_in_existing(fp, fi), id=item.GetId())
            menu.AppendSubMenu(sub, t("dirs.follow_existing"))
        panel.PopupMenu(menu)
        menu.Destroy()

    def _get_existing_followers():
        """Get list of (tracking_id, label) for active follower tabs."""
        # Try to get from the parent Jobs workspace
        try:
            # Walk up to find the host with _wx_jobs_controls
            p = panel.GetParent()
            while p:
                controls = getattr(p, "_wx_jobs_controls", None)
                if controls and "output_channels" in controls:
                    tracked = getattr(p, "_wx_jobs_state", {}).get("tracked_outputs", ())
                    return [(item.tracking_id, item.label) for item in tracked]
                p = p.GetParent() if hasattr(p, 'GetParent') else None
        except Exception:
            pass
        return []

    def _is_file_followed(remote_path):
        """Check if a specific file path is already being followed."""
        remote_path = str(remote_path)
        try:
            p = panel.GetParent()
            while p:
                controls = getattr(p, "_wx_jobs_controls", None)
                if controls and "output_channels" in controls:
                    tracked = getattr(p, "_wx_jobs_state", {}).get("tracked_outputs", ())
                    followers = getattr(p, "_wx_jobs_state", {}).get("followers", {})
                    for item in tracked:
                        if str(getattr(item, "path", "")) == remote_path:
                            return True
                    for follower in followers.values():
                        fpath = str(getattr(getattr(follower, "state", None), "path", ""))
                        if fpath == remote_path:
                            return True
                    return False
                p = p.GetParent() if hasattr(p, 'GetParent') else None
        except Exception:
            pass
        return False

    def _follow_in_new_tab(remote_path):
        """Follow a file in a new output channel tab."""
        follow_cb = getattr(panel, "_follow_callback", None)
        if follow_cb:
            follow_cb(remote_path, "new_tab")

    def _follow_in_new_window(remote_path):
        """Follow a file in a new output window."""
        follow_cb = getattr(panel, "_follow_callback", None)
        if follow_cb:
            follow_cb(remote_path, "new_window")

    def _follow_in_existing(remote_path, follower_id):
        """Assign a file to an existing follower tab."""
        follow_cb = getattr(panel, "_follow_callback", None)
        if follow_cb:
            follow_cb(remote_path, "existing", follower_id)

    def run_operation(action, selected, target_dir=None, *, from_paste=False):
        tstate = active_tab_state()
        if not tstate:
            return
        if not operation or action in {"open", "edit", "edit_new_window"} or (not selected and action not in {"new_folder", "new_file", "upload", "paste"}):
            return
        if action == "delete" and not confirm_remote_delete(
            [_entry_name(item) for item in selected], str(tstate["path"])
        ):
            return
        destination = ""
        operation_paths = selected
        if action == "new_file":
            destination = str(target_dir or "")
        elif action == "new_folder":
            dialog = wx.TextEntryDialog(host, t("dirs.new_folder"), t("dirs.new_folder"))
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
            dialog = wx.TextEntryDialog(host, t(title_key), t(title_key), default)
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
            dialog = wx.DirDialog(host, t("dirs.local_destination"))
            try:
                if dialog.ShowModal() != wx.ID_OK:
                    return
                destination = dialog.GetPath()
            finally:
                dialog.Destroy()
        elif action == "upload":
            dialog = wx.FileDialog(host, t("ftp.upload_selected"), style=wx.FD_OPEN | wx.FD_MULTIPLE)
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

    view.run_direct_operation = run_direct_operation
    view.open_in_editor = open_in_editor
    view._show_follow_menu = _show_follow_menu
    view._get_existing_followers = _get_existing_followers
    view._is_file_followed = _is_file_followed
    view._follow_in_new_tab = _follow_in_new_tab
    view._follow_in_new_window = _follow_in_new_window
    view._follow_in_existing = _follow_in_existing
    view.run_operation = run_operation
