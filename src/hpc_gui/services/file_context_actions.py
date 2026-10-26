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
        return len(self.effective_paths) == 1 and not self.effective_types[0]

    @property
    def one_dir(self) -> bool:
        return len(self.effective_paths) == 1 and self.effective_types[0]

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


# W65 r12: narrow host-owned File-context contribution for OpenFOAM case
# actions. Contribution ids are code-owned here (never manifest-derived);
# visibility additionally requires the verified plugin identity, the
# per-action capability, a single case target, and the readiness flag.
# Dispatch stays a safe no-op returning (False, reason) until a host run
# path is VM-proven. Local/remote legs are mirrored.
OPENFOAM_FILE_CONTEXT_IDS = ("of.newCase", "of.openStudio", "of.validate", "of.createJob")

OPENFOAM_FILE_CONTEXT_READY = False

OPENFOAM_FILE_CONTEXT_PENDING_REASON = (
    "openfoam file-context binding pending readiness "
    "(not shown; no execution)"
)

OPENFOAM_FILE_CONTEXT_NO_RUN_PATH_REASON = (
    "no verified host run path for openfoam file-context action "
    "(explicitly unsupported; no execution)"
)

_OPENFOAM_FILE_CONTEXT_PLUGINS = frozenset({"openfoam-case-studio", "openfoam-linter"})
_OPENFOAM_FILE_CONTEXT_PUBLISHER = "HPC Client GUI"

_OPENFOAM_FILE_CONTEXT_CAPABILITIES = {
    "of.newCase": ("application-tools",),
    "of.openStudio": ("application-tools",),
    "of.createJob": ("application-tools",),
    "of.validate": ("lint-rules", "linter-tool"),
}


def is_openfoam_file_context_ready(plugin=None) -> bool:
    """Return True only when an OpenFOAM file-context path is proven.

    R12 always returns False (code-owned flag above): contribution ids and
    capability checks are live, but nothing is shown and nothing executes.
    Reactivation needs an installed OpenFOAM package identity plus a
    VM-verified host run path.
    """
    return bool(OPENFOAM_FILE_CONTEXT_READY)


def openfoam_file_context_actions(selection: FileContextSelection, plugin, *, remote: bool = False) -> tuple[str, ...]:
    """Return validated of.* contribution ids for a case target, else ().

    The manifest cannot self-authorize: the plugin id/publisher are checked
    against the code-owned identity above and each action requires its
    capability. Multi-select, background and empty selections yield ().
    """
    _ = remote  # local/remote legs are mirrored; kept for call-site clarity
    if not is_openfoam_file_context_ready(plugin):
        return ()
    manifest = getattr(plugin, "manifest", None)
    if manifest is None:
        return ()
    if getattr(manifest, "id", None) not in _OPENFOAM_FILE_CONTEXT_PLUGINS:
        return ()
    if getattr(manifest, "publisher", None) != _OPENFOAM_FILE_CONTEXT_PUBLISHER:
        return ()
    if not (selection.one_file or selection.one_dir):
        return ()
    caps = set(getattr(manifest, "capabilities", None) or ())
    return tuple(
        action for action in OPENFOAM_FILE_CONTEXT_IDS
        if any(cap in caps for cap in _OPENFOAM_FILE_CONTEXT_CAPABILITIES[action])
    )


def dispatch_openfoam_file_context_action(action: str, plugin, selection=None) -> tuple[bool, str]:
    """Safe no-op dispatch for of.* file-context actions.

    Always returns (False, reason): unknown ids, missing plugin identity,
    missing capability, pending readiness, or no verified run path. Never
    executes solver/HPC commands.
    """
    if action not in _OPENFOAM_FILE_CONTEXT_CAPABILITIES:
        return False, f"unknown file-context action {action!r}"
    manifest = getattr(plugin, "manifest", None)
    if manifest is None or getattr(manifest, "id", None) is None:
        return False, "plugin is not installed or missing manifest"
    if getattr(manifest, "id", None) not in _OPENFOAM_FILE_CONTEXT_PLUGINS:
        return False, f"plugin {getattr(manifest, 'id', '?')} is not an OpenFOAM case plugin"
    if getattr(manifest, "publisher", None) != _OPENFOAM_FILE_CONTEXT_PUBLISHER:
        return False, "plugin publisher is not approved by the application"
    required = _OPENFOAM_FILE_CONTEXT_CAPABILITIES[action]
    caps = set(getattr(manifest, "capabilities", None) or ())
    if not any(cap in caps for cap in required):
        return False, f"plugin {manifest.id} lacks required capability for {action!r}: needs {required}"
    if not is_openfoam_file_context_ready(plugin):
        return False, OPENFOAM_FILE_CONTEXT_PENDING_REASON
    return False, OPENFOAM_FILE_CONTEXT_NO_RUN_PATH_REASON


def is_openfoam_file_context_action(action: str) -> bool:
    """Return True for the narrow W65 of.* file-context contribution ids."""
    return action in _OPENFOAM_FILE_CONTEXT_CAPABILITIES


def visible_actions_with_openfoam(selection: FileContextSelection, *, remote: bool, plugins=()) -> tuple[str, ...]:
    """Base visible actions plus validated of.* contributions, in order.

    Readiness False (the default) yields exactly ``visible_actions()``:
    nothing is shown and nothing executes. When a host/test explicitly
    simulates the ready state, validated per-plugin of.* ids are appended
    after the base order; unknown or spoofed plugins contribute nothing.
    """
    base = visible_actions(selection, remote=remote)
    extra: list[str] = []
    for plugin in plugins or ():
        for action in openfoam_file_context_actions(selection, plugin, remote=remote):
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
           "OPENFOAM_FILE_CONTEXT_IDS", "OPENFOAM_FILE_CONTEXT_READY", "OPENFOAM_FILE_CONTEXT_PENDING_REASON", "OPENFOAM_FILE_CONTEXT_NO_RUN_PATH_REASON",
           "is_openfoam_file_context_ready", "openfoam_file_context_actions", "dispatch_openfoam_file_context_action",
           "is_openfoam_file_context_action", "visible_actions_with_openfoam"]
