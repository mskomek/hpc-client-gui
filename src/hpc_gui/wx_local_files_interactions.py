"""Private wx local-file interactions component."""

from hpc_gui.core.i18n import t
from hpc_gui.services.file_context_actions import (
    context_selection as context_selection,
    dispatch_openfoam_file_context_action as dispatch_openfoam_file_context_action,
    is_openfoam_file_context_action as is_openfoam_file_context_action,
    visible_actions as visible_actions,
    visible_actions_with_openfoam as visible_actions_with_openfoam,
)
from hpc_gui.wx_local_files_model import LocalEntry
from hpc_gui.wx_smart_file_open import open_local_file


def _openfoam_plugins(view) -> tuple:
    """Installed OpenFOAM plugins offered to the local File context menu.

    Read from the optional ``openfoam_file_context_plugins`` view
    attribute (iterable or zero-argument provider); absent means no
    contribution. Never raises: failures yield no plugins.
    """
    provider = getattr(view, "openfoam_file_context_plugins", None)
    if provider is None:
        return ()
    if callable(provider):
        try:
            provider = provider()
        except Exception:
            return ()
    try:
        return tuple(provider or ())
    except TypeError:
        return ()


def local_menu_actions(selection, plugins, *, upload=True) -> tuple:
    """Real local menu composition: base actions + validated of.* ids.

    This is the exact composition used by :func:`context_menu` below.
    Readiness False yields the legacy base order unchanged. Only of.*
    ids are ever appended; availability filtering stays with the base.
    """
    base = tuple(
        action for action in visible_actions(selection, remote=False)
        if action != "upload" or upload
    )
    extra = visible_actions_with_openfoam(selection, remote=False, plugins=plugins)
    of_only = [action for action in extra if is_openfoam_file_context_action(action)]
    return base + tuple(action for action in of_only if action not in base)


def run_openfoam_file_context_action(action, selection, plugins) -> tuple:
    """Fail-closed of.* dispatch for the local menu (W65 r13).

    Always returns ``(False, reason)``: readiness False yields the pending
    reason, a simulated-ready state yields the no-run-path reason. Never
    touches the local model, dialogs, solver or HPC paths.
    """
    target = next(iter(plugins or ()), None)
    return dispatch_openfoam_file_context_action(action, target, selection)

def install_interactions(view):
    active_tab_state = view.active_tab_state
    create_tab = view.create_tab
    host = view.host
    labels = view.labels
    model = view.model
    navigate = view.navigate
    notebook = view.notebook
    open_editor = view.open_editor
    path_ctrl = view.path_ctrl
    refresh = view.refresh
    run_action = view.run_action
    state = view.state
    tab_label = view.tab_label
    upload = view.upload
    wx = view.wx

    def visible_actions(*args, **kwargs):
        return view.visible_actions(*args, **kwargs)

    def is_parent_entry(entry, tstate):
        parent = tstate["path"].parent
        return parent != tstate["path"] and entry.path == parent

    def activate(event) -> None:
        tstate = active_tab_state()
        if not tstate:
            return
        idx = event.GetIndex()
        if idx < 0 or idx >= len(tstate["entries"]):
            return
        entry = tstate["entries"][idx]
        if entry.is_dir:
            navigate(entry.path)
            refresh()
        else:
            open_local_file(wx, host, entry.path, open_editor)

    def middle_click(event) -> None:
        tstate = active_tab_state()
        if not tstate:
            event.Skip()
            return
        listing = tstate["listing"]
        # Use HitTest to find entry under cursor
        pos = event.GetPosition()
        # For middle down, position is client coordinates
        idx, _flags = listing.HitTest(pos)
        if idx >= 0 and idx < len(tstate["entries"]):
            entry = tstate["entries"][idx]
            if entry.is_dir:
                # open in new tab
                model.new_tab(entry.path)
                # create visible tab
                new_entry = create_tab(entry.path)
                notebook.AddPage(new_entry["panel"], tab_label(entry.path), True)
                # sync model active index
                model.active_tab = notebook.GetSelection()
                model.current_path = entry.path
                try:
                    path_ctrl.SetValue(str(entry.path))
                except Exception:
                    pass
                if hasattr(host, "_wx_local_controls"):
                    host._wx_local_controls["listing"] = new_entry["listing"]
                refresh()
                return
        event.Skip()

    def context_menu(event) -> None:
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
        entry = entries[index] if 0 <= index < len(entries) else None
        if entry and is_parent_entry(entry, tstate):
            return
        # gather selected entries for active tab
        selected = [item for idx2, item in enumerate(entries) if listing.IsSelected(idx2) and not is_parent_entry(item, tstate)]
        state["context_target"] = entry.path if entry and entry.is_dir else tstate["path"]
        selection = context_selection(
            str(entry.path) if entry else None,
            entry.is_dir if entry else None,
            tuple(str(item.path) for item in selected),
            tuple(item.is_dir for item in selected),
            background=index < 0 and not keyboard_context,
        )
        menu = wx.Menu()
        plugins = _openfoam_plugins(view)
        actions = local_menu_actions(selection, plugins, upload=bool(upload))
        for action in actions:
            item = menu.Append(wx.ID_ANY, t(labels.get(action, "help.help_title")))
            if is_openfoam_file_context_action(action):
                listing.Bind(wx.EVT_MENU, lambda _event, action=action: run_openfoam_file_context_action(action, selection, plugins), item)
            else:
                listing.Bind(wx.EVT_MENU, lambda _event, action=action: run_action(action), item)
        listing.PopupMenu(menu)
        menu.Destroy()

    def selected_entries() -> list[LocalEntry]:
        tstate = active_tab_state()
        if not tstate:
            return []
        listing = tstate["listing"]
        entries = tstate["entries"]
        return [entry for idx2, entry in enumerate(entries) if listing.IsSelected(idx2) and not is_parent_entry(entry, tstate)]

    def key_down(event) -> None:
        # Use active listing; if no selection handle accordingly
        tstate = active_tab_state()
        if not tstate:
            event.Skip()
            return
        listing = tstate["listing"]
        if event.ControlDown() and event.GetKeyCode() in (ord("C"), ord("X"), ord("V")):
            run_action({ord("C"): "copy", ord("X"): "cut", ord("V"): "paste"}[event.GetKeyCode()])
            return
        if event.ControlDown() and event.GetKeyCode() == ord("A"):
            for index in range(listing.GetItemCount()):
                entry = tstate["entries"][index]
                listing.Select(index, not is_parent_entry(entry, tstate))
            return
        # REMOVED: Backspace parent navigation for local (per contract)
        actions = {wx.WXK_F2: "rename", wx.WXK_DELETE: "delete", wx.WXK_F5: "refresh"}
        action = actions.get(event.GetKeyCode())
        if action:
            state["context_target"] = None
            run_action(action)
            return
        event.Skip()

    view.activate = activate
    view.middle_click = middle_click
    view.context_menu = context_menu
    view.selected_entries = selected_entries
    view.key_down = key_down
