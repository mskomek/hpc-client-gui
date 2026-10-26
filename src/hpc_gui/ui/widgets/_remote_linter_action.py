"""Focused OpenFOAM Linter action wiring for the SFTP context menu."""

from __future__ import annotations


def build_remote_linter_action(menu, path: str | None, *, is_directory: bool):
    if not path:
        return None
    from hpc_gui.core.i18n import t
    from hpc_gui.services.openfoam_file_dispatch import active_linter, supports_remote_target

    if not supports_remote_target(path, is_directory=is_directory):
        return None
    plugin = active_linter()
    if plugin is None:
        return None
    from hpc_gui.services.plugin_menu_actions import can_execute_action

    allowed, reason = can_execute_action("openfoam.validate", plugin)
    action = menu.addAction(t("openfoam.linter_title"))
    action.setEnabled(allowed)
    if reason:
        action.setToolTip(reason)
    return action


def dispatch_remote_linter(widget, paths, session) -> bool:
    from hpc_gui.services.openfoam_file_dispatch import dispatch_linter

    return dispatch_linter(
        paths,
        host_window=widget.window(),
        session_state={"session": session, "remote": True},
    )
