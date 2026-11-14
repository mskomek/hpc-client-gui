"""Framework-neutral file context selection and action eligibility."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FileContextSelection:
    clicked_path: str | None
    clicked_is_dir: bool | None
    selected_paths: tuple[str, ...]
    selected_types: tuple[bool, ...]
    background: bool = False

    @property
    def effective_paths(self) -> tuple[str, ...]:
        if self.background:
            return ()
        if self.clicked_path is None:
            return self.selected_paths
        if self.clicked_path in self.selected_paths:
            return self.selected_paths
        return (self.clicked_path,)

    @property
    def effective_types(self) -> tuple[bool, ...]:
        if self.background or self.clicked_path is None:
            return self.selected_types
        if self.clicked_path in self.selected_paths:
            return self.selected_types
        return (bool(self.clicked_is_dir),)

    @property
    def one_file(self) -> bool:
        return len(self.effective_paths) == 1 and len(self.effective_types) == 1 and not self.effective_types[0]

    @property
    def one_dir(self) -> bool:
        return len(self.effective_paths) == 1 and len(self.effective_types) == 1 and self.effective_types[0]

    @property
    def has_selection(self) -> bool:
        return bool(self.effective_paths)


LOCAL_ACTIONS = (
    "open", "open_with", "edit", "edit_new_window", "run_shell", "upload", "rename",
    "delete", "copy", "cut", "paste", "copy_path", "refresh", "new_tab",
    "new_folder",
)
REMOTE_ACTIONS = (
    "open", "edit", "edit_new_window", "run_shell", "download", "upload", "rename",
    "delete", "copy", "move", "paste", "copy_path", "refresh", "new_folder",
    "new_file", "new_tab", "follow_track", "chmod", "submit_slurm", "favorite",
)


# W65: narrow host-owned File-context contribution for OpenFOAM actions.
# Contribution ids and owning plugin identities are code-owned; the live
# API 3 trust gate and framework callback are checked for every menu build
# and again when the user selects an action.
OPENFOAM_FILE_CONTEXT_IDS = ("of.newCase", "of.openStudio", "of.validate", "of.createJob")
_FILE_ACTIONS = {
    "of.newCase": "openfoam.new_case",
    "of.openStudio": "openfoam.open_studio",
    "of.validate": "openfoam.validate",
    "of.createJob": "openfoam.create_job_draft",
}


def installed_openfoam_file_context_plugins() -> tuple:
    """Load active OpenFOAM packages through the normal host plugin loader."""
    try:
        from hpc_gui.plugins.loader import load_installed_plugins
        from hpc_gui.plugins.trusted_api3 import API3_LINTER_ID, API3_STUDIO_ID

        result = load_installed_plugins()
    except Exception:
        return ()
    owners = {API3_STUDIO_ID, API3_LINTER_ID}
    return tuple(
        plugin for plugin in getattr(result, "plugins", ())
        if getattr(getattr(plugin, "manifest", None), "id", None) in owners
    )


def _owner_actions(plugin) -> tuple[str, ...]:
    try:
        from hpc_gui.plugins.trusted_api3 import API3_LINTER_ID, API3_STUDIO_ID

        plugin_id = plugin.manifest.id
    except Exception:
        return ()
    if plugin_id == API3_STUDIO_ID:
        return ("of.newCase", "of.openStudio", "of.createJob")
    if plugin_id == API3_LINTER_ID:
        return ("of.validate",)
    return ()


def openfoam_file_context_plugin(action: str, plugins=()):
    """Resolve an action to its code-owned plugin identity, never list order."""
    owner_id = {
        "of.newCase": "org.hpcclient.openfoamcasestudio",
        "of.openStudio": "org.hpcclient.openfoamcasestudio",
        "of.createJob": "org.hpcclient.openfoamcasestudio",
        "of.validate": "org.hpcclient.openfoamlint",
    }.get(action)
    if owner_id is None:
        return None
    return next(
        (plugin for plugin in plugins or () if getattr(getattr(plugin, "manifest", None), "id", None) == owner_id),
        None,
    )


def wx_file_context_host(view, selection, *, remote=False):
    """Build the framework adapter from the live file panel and session."""
    from hpc_gui.services.wx_plugin_menu_host import WxPluginMenuHost

    editor_page = getattr(view, "host", view)
    session_state = getattr(editor_page, "_wx_openfoam_session_state", {})
    if not isinstance(session_state, dict):
        session_state = {}
    host = WxPluginMenuHost(
        editor_page=editor_page,
        initial_paths=selection.effective_paths,
        session_state=session_state,
        remote=remote,
    )
    return host, session_state


def _remote_session_available(session_state) -> bool:
    if not isinstance(session_state, dict):
        return False
    session = session_state.get("session")
    return isinstance(session, dict) and session.get("files") is not None


def _target_is_supported(action, selection, *, remote, session_state) -> bool:
    paths = selection.effective_paths
    if len(paths) != 1 or not (selection.one_file or selection.one_dir):
        return False
    path = paths[0]
    is_directory = selection.one_dir
    if remote:
        if not _remote_session_available(session_state):
            return False
        from hpc_gui.services.openfoam_file_dispatch import supports_remote_target

        if not supports_remote_target(path, is_directory=is_directory):
            return False
        return action == "of.validate" or is_directory
    if action == "of.validate":
        from hpc_gui.services.openfoam_file_dispatch import supports_local_targets

        return supports_local_targets(paths)
    if not is_directory:
        return False
    from hpc_gui.openfoam_core.local_paths import require_local_path_without_links

    try:
        target = require_local_path_without_links(path)
        if not target.is_dir():
            return False
        if action == "of.newCase":
            return True
        from hpc_gui.services.openfoam_file_dispatch import supports_local_targets

        return supports_local_targets(paths)
    except (OSError, ValueError):
        return False


def is_openfoam_file_context_ready(plugin=None, *, host=None) -> bool:
    """Check the exact API 3 trust gate and, when supplied, real host methods."""
    actions = _owner_actions(plugin)
    if not actions:
        return False
    from hpc_gui.services.plugin_menu_actions import can_execute_action

    return any(can_execute_action(_FILE_ACTIONS[action], plugin, host=host)[0] for action in actions)


def openfoam_file_context_actions(
    selection: FileContextSelection,
    plugin,
    *,
    remote: bool = False,
    host=None,
    session_state=None,
) -> tuple[str, ...]:
    """Return safe actions for one supported path and an active pinned plugin."""
    from hpc_gui.services.plugin_menu_actions import can_execute_action

    actions = []
    for action in _owner_actions(plugin):
        if not _target_is_supported(action, selection, remote=remote, session_state=session_state):
            continue
        allowed, _reason = can_execute_action(_FILE_ACTIONS[action], plugin, host=host)
        if allowed:
            actions.append(action)
    return tuple(action for action in OPENFOAM_FILE_CONTEXT_IDS if action in actions)


def dispatch_openfoam_file_context_action(
    action: str,
    plugin,
    selection=None,
    *,
    remote: bool = False,
    host=None,
    session_state=None,
) -> tuple[bool, str]:
    """Dispatch only through the host-owned API 3 menu controller."""
    if action not in _FILE_ACTIONS:
        return False, f"unknown file-context action {action!r}"
    if action not in _owner_actions(plugin):
        return False, "plugin is not the approved owner for this OpenFOAM action"
    if selection is None or not _target_is_supported(
        action, selection, remote=remote, session_state=session_state
    ):
        return False, "selected path is unsupported, unsafe, or no longer available"
    host_action = _FILE_ACTIONS[action]
    from hpc_gui.services.plugin_menu_actions import can_execute_action, dispatch_plugin_menu_action

    allowed, reason = can_execute_action(host_action, plugin, host=host)
    if not allowed:
        return False, reason
    if host is None:
        return False, "wx OpenFOAM host callback is unavailable"
    if dispatch_plugin_menu_action(host_action, plugin, host):
        return True, ""
    return False, "OpenFOAM action could not open its verified wx page"


def is_openfoam_file_context_action(action: str) -> bool:
    """Return True for the narrow W65 of.* file-context contribution ids."""
    return action in _FILE_ACTIONS


def visible_actions_with_openfoam(
    selection: FileContextSelection,
    *,
    remote: bool,
    plugins=(),
    host=None,
    session_state=None,
) -> tuple[str, ...]:
    """Base actions plus dynamically trusted OpenFOAM callbacks, in order."""
    base = visible_actions(selection, remote=remote)
    extra: list[str] = []
    for plugin in plugins or ():
        for action in openfoam_file_context_actions(
            selection, plugin, remote=remote, host=host, session_state=session_state
        ):
            if action not in extra:
                extra.append(action)
    ordered = [action for action in OPENFOAM_FILE_CONTEXT_IDS if action in extra]
    return tuple(base) + tuple(ordered)


def _eligible(selection: FileContextSelection, remote: bool) -> frozenset[str]:
    if not selection.has_selection:
        return frozenset({"new_folder", "paste", "refresh", "upload"})
    actions = {"copy", "cut", "paste", "delete", "refresh", "copy_path"}
    if remote:
        actions.discard("cut")
        actions.update({"upload", "move"})
        if selection.one_file:
            actions.update({"open", "edit", "edit_new_window", "download", "rename", "follow_track", "chmod", "submit_slurm", "favorite"})
        elif selection.one_dir:
            actions.update({"open", "download", "upload", "new_folder", "new_file", "new_tab", "favorite"})
        else:
            actions.update({"download"})
    elif selection.one_file:
        actions.update({"open", "open_with", "edit", "edit_new_window", "upload", "rename"})
    elif selection.one_dir:
        actions.update({"open", "upload", "new_folder", "new_tab"})
    else:
        actions.update({"upload"})
    if selection.one_file and selection.effective_paths[0].lower().endswith((".sh", ".bash", ".slurm", ".sbatch")):
        actions.add("run_shell")
    return frozenset(actions)


def visible_actions(selection: FileContextSelection, *, remote: bool) -> tuple[str, ...]:
    order = REMOTE_ACTIONS if remote else LOCAL_ACTIONS
    allowed = _eligible(selection, remote)
    return tuple(action for action in order if action in allowed)


def context_selection(
    clicked_path: str | None,
    clicked_is_dir: bool | None,
    selected_paths: tuple[str, ...] = (),
    selected_types: tuple[bool, ...] = (),
    *,
    background: bool = False,
) -> FileContextSelection:
    return FileContextSelection(
        clicked_path,
        clicked_is_dir,
        tuple(selected_paths),
        tuple(selected_types),
        background,
    )


FILE_CONTEXT_LABEL_KEYS = {
    "open": "editor.open", "open_with": "files.open_with", "edit": "dirs.edit",
    "edit_new_window": "dirs.edit_new_window", "upload": "dirs.upload", "download": "dirs.download",
    "download_as": "dirs.download_as",
    "rename": "dirs.rename", "delete": "dirs.delete", "copy": "dirs.copy", "cut": "dirs.move",
    "move": "dirs.move", "paste": "dirs.paste", "copy_path": "dirs.copy_path", "refresh": "dirs.refresh",
    "new_tab": "dirs.new_tab", "new_folder": "dirs.new_folder", "new_file": "dirs.new_file",
    "run_shell": "dirs.run_shell_terminal",
    "follow_track": "dirs.follow_track",
    "chmod": "dirs.permissions_title", "submit_slurm": "dirs.submit_sbatch",
    "favorite": "dirs.favorite_add_item",
    # W65 r12: of.* contribution ids reuse the paired openfoam.* i18n keys
    # (TR+EN ship together; see tests/test_w65_r11_host.py key parity).
    "of.newCase": "openfoam.new_case", "of.openStudio": "openfoam.open_studio",
    "of.validate": "openfoam.validate", "of.createJob": "openfoam.create_job",
}


def summarize_delete_targets(names, location, *, max_names: int = 5):
    """Framework-neutral delete-target summary (W23 FILE-035/036).

    Returns (count, location_text, names_text) with at most ``max_names``
    item names listed and a "+N more" suffix when truncated. Empty names
    yield an empty names_text; callers fall back to the generic confirm.
    """
    items = [str(name) for name in (names or []) if str(name)]
    where = str(location or "")
    if not items:
        return (0, where, "")
    shown = items[: max(1, int(max_names))]
    suffix = "" if len(items) <= len(shown) else f" (+{len(items) - len(shown)} more)"
    return (len(items), where, ", ".join(shown) + suffix)


def delete_confirm_message(names, location, *, max_names: int = 5) -> str:
    """English fallback delete-confirmation text naming the actual target."""
    count, where, shown = summarize_delete_targets(names, location, max_names=max_names)
    if count <= 0:
        return "Delete the selected items?"
    if where:
        return f"Delete {count} selected item(s) from {where}?\n{shown}"
    return f"Delete {count} selected item(s)?\n{shown}"


__all__ = ["FILE_CONTEXT_LABEL_KEYS", "FileContextSelection", "context_selection", "visible_actions", "summarize_delete_targets", "delete_confirm_message",
           "OPENFOAM_FILE_CONTEXT_IDS", "installed_openfoam_file_context_plugins",
           "openfoam_file_context_plugin", "wx_file_context_host",
           "is_openfoam_file_context_ready", "openfoam_file_context_actions", "dispatch_openfoam_file_context_action",
           "is_openfoam_file_context_action", "visible_actions_with_openfoam"]
