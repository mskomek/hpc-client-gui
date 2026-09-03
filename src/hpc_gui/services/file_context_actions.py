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
        if self.background or self.clicked_path is None:
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
    "open", "open_with", "edit", "edit_new_window", "upload", "rename",
    "delete", "copy", "cut", "paste", "copy_path", "refresh", "new_tab",
    "new_folder",
)
REMOTE_ACTIONS = (
    "open", "edit", "edit_new_window", "download", "upload", "rename",
    "delete", "copy", "move", "paste", "copy_path", "refresh", "new_folder",
    "new_tab",
)


def _eligible(selection: FileContextSelection, remote: bool) -> frozenset[str]:
    if not selection.has_selection:
        return frozenset({"new_folder", "paste", "refresh"})
    actions = {"copy", "cut", "paste", "delete", "refresh", "copy_path"}
    if remote:
        actions.discard("cut")
        if selection.one_file:
            actions.update({"open", "edit", "edit_new_window", "download", "rename"})
        elif selection.one_dir:
            actions.update({"open", "download", "new_tab"})
        else:
            actions.update({"download"})
    elif selection.one_file:
        actions.update({"open", "open_with", "edit", "edit_new_window", "upload", "rename"})
    elif selection.one_dir:
        actions.update({"open", "new_folder", "new_tab"})
    else:
        actions.update({"upload"})
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
) -> FileContextSelection:
    return FileContextSelection(
        clicked_path,
        clicked_is_dir,
        tuple(selected_paths),
        tuple(selected_types),
        clicked_path is None,
    )


__all__ = ["FileContextSelection", "context_selection", "visible_actions"]
