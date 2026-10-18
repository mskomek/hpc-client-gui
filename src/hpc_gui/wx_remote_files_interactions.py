"""Private wx remote-file interactions component."""

from pathlib import PurePosixPath

from hpc_gui.core.i18n import t
from hpc_gui.services.file_context_actions import FILE_CONTEXT_LABEL_KEYS, context_selection
from hpc_gui.services.file_open import detect_file_type, smart_open_preferences
from hpc_gui.wx_smart_file_open import choose_smart_open


def install_interactions(view):
    _available = view._available
    _current_navigation_store = view._current_navigation_store
    active_tab_state = view.active_tab_state
    chmod = view.chmod
    chmod_supported = view.chmod_supported
    create_tab = view.create_tab
    host = view.host
    load = view.load
    model = view.model
    navigate = view.navigate
    notebook = view.notebook
    open_editor = view.open_editor
    open_in_editor = view.open_in_editor
    operation = view.operation
    operation_supported = view.operation_supported
    open_external = view.open_external
    panel = view.panel
    path = view.path
    run_action = view.run_action
    submit_slurm = view.submit_slurm
    submit_slurm_supported = view.submit_slurm_supported
    tab_label = view.tab_label
    wx = view.wx

    def visible_actions(*args, **kwargs):
        return view.visible_actions(*args, **kwargs)

    def is_parent_entry(entry, tstate):
        parent = PurePosixPath(tstate["path"]).parent
        return parent != PurePosixPath(tstate["path"]) and entry.path == str(parent)

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
        selected = tuple(entry.path for index, entry in enumerate(tstate["entries"]) if listing.IsSelected(index) and not is_parent_entry(entry, tstate))
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
            return
        file_type = detect_file_type(entry.path)
        if file_type.category == "text" and open_editor:
            open_in_editor(entry.path, open_editor)
            return
        preferred = smart_open_preferences().get(file_type.extension)
        if preferred == "system" and not file_type.executable and callable(open_external):
            open_external(entry.path, int(getattr(entry, "size", 0) or 0))
            return
        if preferred == "editor" and file_type.editable and open_editor:
            open_in_editor(entry.path, open_editor)
            return
        action = choose_smart_open(
            wx, panel, name=entry.path.rsplit("/", 1)[-1],
            size=int(getattr(entry, "size", 0) or 0), has_editor=bool(open_editor),
        )
        if action == "editor" and open_editor:
            open_in_editor(entry.path, open_editor)
        elif action == "system" and callable(open_external):
            open_external(entry.path, int(getattr(entry, "size", 0) or 0))

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
                host._wx_remote_controls["listing"] = new_entry["listing"]
                host._wx_remote_controls["path"] = path
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
        clicked = entries[index] if 0 <= index < len(entries) else None
        if clicked and is_parent_entry(clicked, tstate):
            return
        selected_entries = tuple(entry for idx, entry in enumerate(entries) if listing.IsSelected(idx) and not is_parent_entry(entry, tstate))
        selection = context_selection(
            clicked.path if clicked else None,
            clicked.is_dir if clicked else None,
            tuple(entry.path for entry in selected_entries),
            tuple(entry.is_dir for entry in selected_entries),
            background=index < 0 and not keyboard_context,
        )
        selected = selection.effective_paths
        menu = wx.Menu()
        candidate_actions = ("open", "edit", "edit_new_window", "run_shell", "follow_track", "download", "upload", "copy", "move", "rename", "delete", "paste", "copy_path", "refresh", "new_folder", "new_file", "chmod", "submit_slurm", "favorite", "new_tab")
        allowed = visible_actions(selection, remote=True)
        if not callable(getattr(panel, "_follow_callback", None)):
            allowed = tuple(action for action in allowed if action != "follow_track")
        if not _available(chmod, chmod_supported):
            allowed = tuple(action for action in allowed if action != "chmod")
        if not _available(submit_slurm, submit_slurm_supported):
            allowed = tuple(action for action in allowed if action != "submit_slurm")
        if not _available(operation, operation_supported):
            allowed = tuple(action for action in allowed if action != "new_file")
        if _current_navigation_store() is None:
            allowed = tuple(action for action in allowed if action != "favorite")
        actions = tuple(action for action in candidate_actions if action in allowed)
        labels = FILE_CONTEXT_LABEL_KEYS
        for action in actions:
            item = menu.Append(wx.ID_ANY, t(labels.get(action, f"dirs.{action}")))
            target_dir = clicked.path if clicked and clicked.is_dir else tstate["path"]
            listing.Bind(wx.EVT_MENU, lambda _event, action=action, target=target_dir: run_action(action, selected, target), item)
        listing.PopupMenu(menu)
        menu.Destroy()

    view.key_down = key_down
    view.activate = activate
    view.middle_click = middle_click
    view.context = context
