"""FTP activity-menus leaf for the file-manager FTP widget.

Owns ``ActivityMenusMixin`` (queue/transfer context menus plus the completion
action) and the shared ``_exec_temporary_menu`` shiboken-lifetime guard used
by the session default menu (imported by ``_ftp_session`` — one-directional
sibling edge, documented here). All controller calls go through duck-typed
controller dispatch reached via ``self``.

Imports Qt plus lower-level config/i18n only — never panels, FTP internals of
other leaves (beyond the documented guard import direction), controllers, or
other branches.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QMenu, QTreeWidget, QWidget

from hpc_gui.config.storage import (
    get_transfer_completion_action,
    set_transfer_completion_action,
)
from hpc_gui.core.i18n import tr as _tr


def _exec_temporary_menu(owner: QWidget, menu: QMenu, position):
    """Run a context menu without dropping its Python wrapper mid-event-loop.

    PySide owns a ``QMenu`` wrapper separately from Qt's parent-child tree.  On
    Windows, allowing a locally-created menu wrapper to be collected while its
    native popup is closing can crash in shiboken.  Keep one strong reference
    for the complete nested menu loop, then defer the native deletion.
    """
    owner._active_context_menu = menu
    try:
        return menu.exec(position)
    finally:
        if getattr(owner, "_active_context_menu", None) is menu:
            owner._active_context_menu = None
        delete_later = getattr(menu, "deleteLater", None)
        if callable(delete_later):
            delete_later()


class ActivityMenusMixin:
    """Activity-menu ownership (mixed into ``TransferActivityPanel``)."""

    def _show_queue_menu(self, pos) -> None:
        self._show_transfer_menu(self.queue_list, pos, "queue")

    def _show_transfer_menu(self, view: QTreeWidget, pos, kind: str) -> None:
        menu = QMenu(self)  # type: ignore[arg-type]
        selected = self._selected_transfer_items(
            view,
            queued_only=kind == "queue",
        )
        controller = self._controller
        pending = bool(getattr(controller, "_pending", []) or []) if controller else False
        running = bool(getattr(controller, "_running", False)) if controller else False
        active = bool(
            getattr(controller, "_active_items", [])
            or getattr(controller, "_active_item", None)
        ) if controller else False
        failed = bool(getattr(controller, "_errors", []) or []) if controller else False
        failed = failed or self.failed_list.topLevelItemCount() > 0
        completed = bool(getattr(controller, "_completed", []) or []) if controller else False
        completed = completed or self.completed_list.topLevelItemCount() > 0
        actions: dict[object, tuple[str, tuple]] = {}

        def add_action(
            label_key: str,
            fallback: str,
            method: str,
            *args,
            enabled: bool = True,
        ) -> None:
            action = menu.addAction(_tr(label_key, fallback))
            action.setEnabled(enabled and self._controller_action_available(method))
            if args and not args[0]:
                action.setEnabled(False)
            actions[action] = (method, args)

        def add_disabled_action(label_key: str, fallback: str, tooltip_key: str) -> None:
            action = menu.addAction(_tr(label_key, fallback))
            action.setEnabled(False)
            tooltip = _tr(tooltip_key, "Not available in this version.")
            if hasattr(action, "setToolTip"):
                action.setToolTip(tooltip)

        def add_priority_menu() -> None:
            priority_menu = menu.addMenu(
                _tr("transfer.set_priority", "Set Priority")
            )
            for priority in ("Highest", "High", "Normal", "Low", "Lowest"):
                action = priority_menu.addAction(
                    _tr(f"transfer.priority_{priority.lower()}", priority)
                )
                action.setEnabled(bool(selected) and self._controller_action_available("set_pending_priority"))
                actions[action] = ("set_pending_priority", (selected, priority))

        def add_completion_menu() -> None:
            completion_menu = menu.addMenu(
                _tr("transfer.after_completion", "Action after queue completion")
            )
            selected_action = get_transfer_completion_action()
            choices = (
                ("none", "transfer.completion_none", "None"),
                ("notification", "transfer.completion_notification", "Show notification bubble"),
                ("attention", "transfer.completion_attention", "Request attention"),
                ("close_once", "transfer.completion_close_once", "Close HPC Client GUI once"),
                ("run_command", "transfer.completion_run_command", "Run command..."),
                ("play_sound", "transfer.completion_play_sound", "Play sound"),
                ("close", "transfer.completion_close", "Close HPC Client GUI"),
                ("reboot_once", "transfer.completion_reboot_once", "Reboot system once"),
                ("shutdown_once", "transfer.completion_shutdown_once", "Shutdown system once"),
                ("suspend_once", "transfer.completion_suspend_once", "Suspend system once"),
            )
            for value, key, fallback in choices:
                action = completion_menu.addAction(_tr(key, fallback))
                if hasattr(action, "setCheckable"):
                    action.setCheckable(True)
                    action.setChecked(value == selected_action)
                if value not in {"none", "notification", "attention", "play_sound"}:
                    action.setEnabled(False)
                    if hasattr(action, "setToolTip"):
                        action.setToolTip(
                            _tr(
                                "transfer.completion_action_unavailable",
                                "This action is not available yet.",
                            )
                        )
                actions[action] = ("set_completion_action", (value,))

        if kind == "queue":
            add_action(
                "transfer.process_queue",
                "Process queue",
                "process_queue",
                enabled=running or active or pending,
            )
            add_action(
                "transfer.stop_remove_all",
                "Stop and remove all",
                "cancel_all",
                enabled=running or active or pending,
            )
            menu.addSeparator()
            add_action(
                "transfer.remove_selected",
                "Remove selected",
                "remove_pending_items",
                selected,
            )
            add_disabled_action(
                "transfer.default_file_exists_action",
                "Default file exists action...",
                "transfer.unavailable_file_exists",
            )
            add_priority_menu()
            add_completion_menu()
            add_disabled_action(
                "transfer.export",
                "Export...",
                "transfer.unavailable_export",
            )
        elif kind == "failed":
            add_action(
                "transfer.retry_selected",
                "Retry selected",
                "retry_failed_items",
                selected,
            )
            add_action(
                "transfer.retry_failed",
                "Retry failed",
                "retry_all_errors",
                enabled=failed,
            )
            menu.addSeparator()
            add_action(
                "transfer.remove_selected",
                "Remove selected",
                "remove_failed_items",
                selected,
            )
            add_action(
                "transfer.clear_failed",
                "Clear failed",
                "clear_failed",
                enabled=failed,
            )
        else:
            add_action(
                "transfer.remove_selected",
                "Remove selected",
                "remove_completed_items",
                selected,
            )
            add_action(
                "transfer.clear_completed",
                "Clear completed",
                "clear_completed",
                enabled=completed,
            )

        chosen = _exec_temporary_menu(self, menu, view.viewport().mapToGlobal(pos))  # type: ignore[arg-type]
        if chosen in actions and chosen.isEnabled():
            method, args = actions[chosen]
            if method == "set_completion_action":
                self._set_completion_action(*args)
            else:
                self._call_controller(method, *args)

    def _set_completion_action(self, action: str) -> None:
        selected = set_transfer_completion_action(action)
        observable = {"none", "notification", "attention", "play_sound"}
        if selected == "play_sound":
            QApplication.beep()
        if selected in observable:
            text = _tr(
                "transfer.completion_action_saved",
                "Completion action saved: {action}",
            ).format(action=selected)
        else:
            text = _tr(
                "transfer.completion_action_unsupported",
                "This completion action was saved but needs confirmation and is not executed.",
            )
        self._set_status_text(text)


__all__ = [
    "ActivityMenusMixin",
    "_exec_temporary_menu",
]
