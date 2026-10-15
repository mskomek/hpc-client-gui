"""Private wx local-file listing component."""

from pathlib import Path
from threading import Thread
from hpc_gui.core.i18n import t
from hpc_gui.services.local_files import list_windows_drives
from hpc_gui.wx_file_list_style import alternate_row_colour
from hpc_gui.wx_file_type_icons import file_type_icon_index, install_file_type_icons
from hpc_gui.wx_local_files_model import format_local_size
from hpc_gui.wx_local_files_support import _format_mtime, _type_label

_COLUMN_FLOORS = (140, 70, 110, 120)

def install_listing(view):
    activate = view.activate
    btn_back = view.btn_back
    btn_drives = view.btn_drives
    btn_forward = view.btn_forward
    btn_parent = view.btn_parent
    btn_refresh = view.btn_refresh
    context_menu = view.context_menu
    host = view.host
    key_down = view.key_down
    middle_click = view.middle_click
    model = view.model
    next_tab_id = view.next_tab_id
    notebook = view.notebook
    path_ctrl = view.path_ctrl
    path_label = view.path_label
    safe_call_after = view.safe_call_after
    state = view.state
    tabs = view.tabs
    threading_lock = view.threading_lock
    wx = view.wx

    def tab_label(path_value: Path) -> str:
        name = path_value.name
        return name or str(path_value) or "Local"

    def active_tab_state():
        sel = notebook.GetSelection()
        if sel < 0 or sel >= len(tabs):
            return tabs[0] if tabs else None
        return tabs[sel]

    def active_listing():
        tstate = active_tab_state()
        return tstate["listing"] if tstate else None

    def current_entries():
        tstate = active_tab_state()
        return tstate["entries"] if tstate else []

    def sync_model_to_active():
        tstate = active_tab_state()
        if not tstate:
            return
        idx = notebook.GetSelection()
        model.active_tab = idx
        if idx < len(model.tabs):
            model.current_path = tstate["path"]
        else:
            # shouldn't happen
            pass

    def refresh_active_tab_label(idx: int | None = None):
        if idx is None:
            idx = notebook.GetSelection()
        if 0 <= idx < len(tabs):
            notebook.SetPageText(idx, tab_label(tabs[idx]["path"]))

    def render_entries(tab_entry, entries, selected_paths=()) -> None:
        selected_paths = set(selected_paths)
        tab_entry["entries"][:] = entries
        listing = tab_entry["listing"]
        try:
            listing.DeleteAllItems()
            stripe = alternate_row_colour(wx)
            for row_index, entry in enumerate(tab_entry["entries"]):
                index = listing.InsertItem(listing.GetItemCount(), entry.path.name)
                listing.SetItemImage(
                    index, file_type_icon_index(entry.path.name, entry.is_dir)
                )
                listing.SetItem(index, 1, format_local_size(entry))
                listing.SetItem(index, 2, _type_label(entry))
                listing.SetItem(index, 3, _format_mtime(getattr(entry, "mtime", None)))
                if row_index % 2:
                    listing.SetItemBackgroundColour(index, stripe)
                if entry.path in selected_paths:
                    listing.Select(index)
        except RuntimeError:
            return

    def refresh(selected_paths=()) -> None:
        tstate = active_tab_state()
        if not tstate:
            return
        with threading_lock:
            if state["closed"] or tstate.get("closed"):
                return
            # increments both global and per-tab generation
            state["view_generation"] += 1
            state["listing_request_id"] += 1
            tstate["view_generation"] += 1
            tstate["listing_request_id"] += 1
            request_id = tstate["listing_request_id"]
            request_generation = tstate["view_generation"]
            requested_path = tstate["path"]
            tab_id = tstate["id"]

        def done(result, error):
            # re-check lifetime in callback (post-queue safety)
            # LIFECYCLE-NATIVE-001 class: drop stale completions after destroy.
            try:
                with threading_lock:
                    # find tab by id (may have been closed)
                    tab_entry = next((tt for tt in tabs if tt["id"] == tab_id), None)
                    if not tab_entry or tab_entry.get("closed"):
                        return
                    current = (
                        not state["closed"]
                        and request_id == tab_entry["listing_request_id"]
                        and request_generation == tab_entry["view_generation"]
                        and requested_path == tab_entry["path"]
                    )
                if not current:
                    return
                try:
                    notebook.GetSelection()
                except Exception:
                    return
                if error:
                    # only show error if this tab is active, otherwise silently ignore? Spec says no error should show in other tab, but stale check above already filters.
                    # If tab is not active, still don't show message box (avoid cross-tab).
                    try:
                        if notebook.GetSelection() == tabs.index(tab_entry):
                            wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
                    except Exception:
                        return
                    return
                # verify controls still alive
                try:
                    if not tab_entry["listing"] or not tab_entry["listing"].IsShownOnScreen() and False:
                        pass
                    # Accessing destroyed control raises exception; check via wx
                    if not tab_entry["listing"]:
                        return
                except Exception:
                    return
                try:
                    # Check if window still exists
                    if not wx.Window.FindWindowById(tab_entry["listing"].GetId()):
                        # fallback: check closed flag already
                        pass
                except Exception:
                    pass
                # Only render if tab still valid; but we update that tab's listing regardless of active
                try:
                    render_entries(tab_entry, result, selected_paths)
                except Exception:
                    return
            except Exception:
                return

        def worker():
            try:
                safe_call_after(done, model.list_entries(requested_path), None)
            except Exception as error:
                safe_call_after(done, (), error)

        Thread(target=worker, daemon=True).start()

    def navigate(target) -> None:
        tstate = active_tab_state()
        if not tstate:
            return
        resolved = Path(target).expanduser().resolve()
        if resolved != tstate["path"]:
            state["view_generation"] += 1
            tstate["view_generation"] += 1
        tstate["path"] = resolved
        # sync model tabs entry
        idx = notebook.GetSelection()
        if 0 <= idx < len(model.tabs):
            model.tabs[idx] = resolved
        model.current_path = resolved
        model.active_tab = idx
        try:
            path_ctrl.SetValue(str(resolved))
        except Exception:
            pass
        refresh_active_tab_label(idx)

    def _apply_column_widths(listing) -> None:
        try:
            for col in (1, 2, 3):
                listing.SetColumnWidth(col, wx.LIST_AUTOSIZE_USEHEADER)
                listing.SetColumnWidth(col, max(_COLUMN_FLOORS[col], listing.GetColumnWidth(col)))
            avail = listing.GetClientSize().GetWidth() or 860
            fixed = sum(listing.GetColumnWidth(c) for c in (1, 2, 3))
            listing.SetColumnWidth(0, max(_COLUMN_FLOORS[0], avail - fixed - 24))
        except Exception:
            pass

    def create_tab(target_path: Path):
        target_path = Path(target_path).expanduser().resolve()
        panel = wx.Panel(notebook)
        listing = wx.ListCtrl(panel, style=wx.LC_REPORT)
        image_list = install_file_type_icons(wx, listing)
        listing.InsertColumn(0, t("dirs.col_name"))
        listing.InsertColumn(1, t("dirs.col_size"))
        listing.InsertColumn(2, t("dirs.col_type"))
        listing.InsertColumn(3, t("dirs.col_mtime"))
        _apply_column_widths(listing)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(listing, 1, wx.EXPAND)
        panel.SetSizer(sizer)
        tab_entry = {"id": next_tab_id[0], "path": target_path, "listing": listing, "entries": [], "view_generation": 0, "listing_request_id": 0, "closed": False, "panel": panel, "image_list": image_list}
        next_tab_id[0] += 1
        tabs.append(tab_entry)
        # sync model
        # caller will handle notebook insertion
        # bind events for this listing
        listing.Bind(wx.EVT_LIST_ITEM_ACTIVATED, activate)
        listing.Bind(wx.EVT_CONTEXT_MENU, context_menu)
        listing.Bind(wx.EVT_KEY_DOWN, key_down)
        listing.Bind(wx.EVT_MIDDLE_DOWN, middle_click)
        # also handle middle click via list event hit test fallback
        return tab_entry

    def _update_back_button():
        try:
            btn_back.Enable(bool(model._history))
            btn_forward.Enable(bool(model._forward))
        except Exception:
            pass

    def show_drives():
        tstate = active_tab_state()
        if not tstate:
            return
        try:
            drives = list_windows_drives()
        except Exception as error:
            wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            return
        # Render drives directly without model navigation; keep history
        lst = tstate["listing"]
        try:
            lst.DeleteAllItems()
            tstate["entries"][:] = []
            stripe = alternate_row_colour(wx)
            # Represent drives as synthetic entries for activation
            for row_index, d in enumerate(drives):
                # d may be LocalEntry from services.local_files (name, path) or Path
                name = getattr(d, "name", None) or getattr(d, "path", None) or str(d)
                path_val = getattr(d, "path", None) or name
                # Create a minimal entry with expected attributes for later activation
                class _Drv:
                    pass
                ent = _Drv()
                ent.path = Path(path_val)
                ent.is_dir = True
                ent.size = 0
                # also keep original for display
                ent._drive_name = str(name)
                tstate["entries"].append(ent)
                idx = lst.InsertItem(lst.GetItemCount(), str(name))
                lst.SetItemImage(idx, file_type_icon_index(str(name), True))
                lst.SetItem(idx, 1, "")
                lst.SetItem(idx, 2, t("dirs.type_folder"))
                lst.SetItem(idx, 3, "")
                if row_index % 2:
                    lst.SetItemBackgroundColour(idx, stripe)
            try:
                path_ctrl.SetValue(t("ftp.drives"))
            except Exception:
                pass
        except RuntimeError:
            return

    def go_back_view():
        if not model.can_go_back():
            return
        try:
            model.go_back()
        except Exception as error:
            wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            return
        tstate = active_tab_state()
        if not tstate:
            return
        idx = notebook.GetSelection()
        tstate["path"] = model.current_path
        if 0 <= idx < len(model.tabs):
            model.tabs[idx] = model.current_path
        try:
            path_ctrl.SetValue(str(model.current_path))
        except Exception:
            pass
        refresh_active_tab_label(idx)
        _update_back_button()
        refresh()

    def go_forward_view():
        if not model.can_go_forward():
            return
        try:
            model.go_forward()
        except Exception as error:
            wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)
            return
        tstate = active_tab_state()
        if not tstate:
            return
        idx = notebook.GetSelection()
        tstate["path"] = model.current_path
        if 0 <= idx < len(model.tabs):
            model.tabs[idx] = model.current_path
        try:
            path_ctrl.SetValue(str(model.current_path))
        except Exception:
            pass
        refresh_active_tab_label(idx)
        _update_back_button()
        refresh()

    def go_parent_view():
        tstate = active_tab_state()
        if not tstate:
            return
        cur = tstate["path"]
        parent = cur.parent
        if parent == cur:
            return
        try:
            navigate(parent)
            refresh()
            _update_back_button()
        except Exception as error:
            wx.MessageBox(str(error), t("login.err_title"), wx.OK | wx.ICON_ERROR)

    def refresh_labels(_language=None):
        host.set_host_title(t("tabs.ftp"))
        try:
            btn_drives.SetLabel(t("ftp.drives"))
            btn_back.SetLabel(t("ftp.back"))
            btn_forward.SetLabel(t("ftp.forward"))
            btn_parent.SetLabel(t("ftp.parent"))
            btn_refresh.SetLabel(t("dirs.refresh"))
            path_label.SetLabel(t("dirs.path"))
        except Exception:
            pass
        for tab_entry in tabs:
            try:
                tab_entry["listing"].SetColumn(0, t("dirs.col_name"))
                tab_entry["listing"].SetColumn(1, t("dirs.col_size"))
                tab_entry["listing"].SetColumn(2, t("dirs.col_type"))
                tab_entry["listing"].SetColumn(3, t("dirs.col_mtime"))
                _apply_column_widths(tab_entry["listing"])
            except RuntimeError:
                continue
        # update tab labels (paths may contain same)
        for idx, te in enumerate(tabs):
            try:
                notebook.SetPageText(idx, tab_label(te["path"]))
            except Exception:
                pass

    view.tab_label = tab_label
    view.active_tab_state = active_tab_state
    view.active_listing = active_listing
    view.current_entries = current_entries
    view.sync_model_to_active = sync_model_to_active
    view.refresh_active_tab_label = refresh_active_tab_label
    view.render_entries = render_entries
    view.refresh = refresh
    view.navigate = navigate
    view._apply_column_widths = _apply_column_widths
    view.create_tab = create_tab
    view._update_back_button = _update_back_button
    view.show_drives = show_drives
    view.go_back_view = go_back_view
    view.go_forward_view = go_forward_view
    view.go_parent_view = go_parent_view
    view.refresh_labels = refresh_labels
