"""Private wx remote-file interactions component."""

from pathlib import PurePosixPath

from hpc_gui.core.i18n import t
from hpc_gui.services.file_context_actions import (
    FILE_CONTEXT_LABEL_KEYS,
    context_selection,
    dispatch_openfoam_file_context_action,
    installed_openfoam_file_context_plugins,
    is_openfoam_file_context_action,
    openfoam_file_context_plugin,
    visible_actions,
    visible_actions_with_openfoam,
    wx_file_context_host,
)
from hpc_gui.services.file_open import detect_file_type, smart_open_preferences
from hpc_gui.wx_smart_file_open import choose_smart_open

# W65 r13: hoisted from context() so the real remote menu composition is
# unit-testable and stays the single source of truth for both legs.
REMOTE_CANDIDATE_ACTIONS = ("open", "edit", "edit_new_window", "run_shell", "follow_track", "download", "upload", "copy", "move", "rename", "delete", "paste", "copy_path", "refresh", "new_folder", "new_file", "chmod", "submit_slurm", "favorite", "new_tab")


def _openfoam_plugins(view) -> tuple:
    """Discover active OpenFOAM packages through the host's verified loader."""
    return installed_openfoam_file_context_plugins()


def remote_menu_actions(
    selection,
    plugins,
    *,
    follow=True,
    chmod=True,
    submit=True,
    operation=True,
    favorites=True,
    host=None,
    session_state=None,
) -> tuple:
    """Real remote menu composition: candidate order ∩ allowed + of.* ids.

    This is the exact composition used by :func:`context` below (via
    install_interactions). Readiness False yields the legacy order
    unchanged.
    """
    allowed = set(visible_actions(selection, remote=True))
    if not follow:
        allowed.discard("follow_track")
    if not chmod:
        allowed.discard("chmod")
    if not submit:
        allowed.discard("submit_slurm")
    if not operation:
        allowed.discard("new_file")
    if not favorites:
        allowed.discard("favorite")
    actions = tuple(action for action in REMOTE_CANDIDATE_ACTIONS if action in allowed)
    extra = visible_actions_with_openfoam(
        selection, remote=True, plugins=plugins, host=host,
        session_state=session_state,
    )
    of_only = [action for action in extra if is_openfoam_file_context_action(action)]
    return actions + tuple(action for action in of_only if action not in actions)


def run_openfoam_file_context_action(
    action,
    selection,
    plugins,
    *,
    host=None,
    session_state=None,
) -> tuple:
    """Invoke the owning pinned plugin through its host-owned wx callback."""
    target = openfoam_file_context_plugin(action, plugins)
    return dispatch_openfoam_file_context_action(
        action, target, selection, remote=True, host=host,
        session_state=session_state,
    )


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
            for index, entry in enumerate(tstate["entries"]):
                listing.Select(index, not is_parent_entry(entry, tstate))
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
        plugins = _openfoam_plugins(view)
        plugin_host, session_state = wx_file_context_host(view, selection, remote=True)
        actions = remote_menu_actions(
            selection, plugins,
            follow=callable(getattr(panel, "_follow_callback", None)),
            chmod=_available(chmod, chmod_supported),
            submit=_available(submit_slurm, submit_slurm_supported),
            operation=_available(operation, operation_supported),
            favorites=_current_navigation_store() is not None,
            host=plugin_host,
            session_state=session_state,
        )
        if "download" in actions and len(selected_entries) == 1 and not selected_entries[0].is_dir:
            actions += ("download_as",)
        labels = FILE_CONTEXT_LABEL_KEYS
        for action in actions:
            item = menu.Append(wx.ID_ANY, t(labels.get(action, f"dirs.{action}")))
            if is_openfoam_file_context_action(action):
                def run_openfoam(_event, action=action):
                    ok, reason = run_openfoam_file_context_action(
                        action, selection, plugins, host=plugin_host,
                        session_state=session_state,
                    )
                    if not ok:
                        wx.MessageBox(reason, t("login.err_title"), wx.OK | wx.ICON_WARNING, parent=panel)

                listing.Bind(wx.EVT_MENU, run_openfoam, item)
                continue
            target_dir = clicked.path if clicked and clicked.is_dir else tstate["path"]
            listing.Bind(wx.EVT_MENU, lambda _event, action=action, target=target_dir: run_action(action, selected, target), item)
        listing.PopupMenu(menu)
        menu.Destroy()

    view.key_down = key_down
    view.activate = activate
    view.middle_click = middle_click
    view.context = context
