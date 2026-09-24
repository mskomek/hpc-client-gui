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


__all__ = ["FILE_CONTEXT_LABEL_KEYS", "FileContextSelection", "context_selection", "visible_actions", "summarize_delete_targets", "delete_confirm_message"]
