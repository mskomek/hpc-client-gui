"""FTP activity-sync leaf for the file-manager FTP widget.

Owns ``ActivitySyncMixin``: transfer-activity records, finished-history merge,
controller attach/detach/finish, status/progress text, list synchronization
from controllers, controller calls, history pruning, selection helpers, and the
control enablement matrix. Table rendering lives in ``_ftp_activity_table``;
menus live in ``_ftp_activity_menus``; all are reached via ``self``.

Imports Qt only — never panels, FTP internals of other leaves, controllers, or
other branches. Controllers stay duck-typed (callback attributes only).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget


class ActivitySyncMixin:
    """Controller-sync ownership (mixed into ``TransferActivityPanel``)."""

    def record(self, event: str, items: list, title: str = "") -> None:
        if event == "controller" and items:
            self.attach_controller(items[0])
            return
        if event == "queued":
            logical_items = self._render_full_list(
                self.queue_list,
                items,
                "Queued",
            )
            self._update_summary(logical_items)
            self._tab_counts["queue"] = len(logical_items)
            self.retranslate_ui()
            return
        if event == "completed":
            self._finished_completed = self._merge_finished_history(
                self._finished_completed, items
            )
            self._sync_lists_from_controller()
            return
        if event == "failed":
            seen = {id(item) for item, _error in self._finished_errors}
            for item in items:
                if (
                    getattr(item, "op", "") in {"upload", "download"}
                    and id(item) not in seen
                ):
                    self._finished_errors.append((item, str(title or "")))
                    seen.add(id(item))
            self._sync_lists_from_controller()

    @staticmethod
    def _merge_finished_history(history: list, items: list) -> list:
        merged = list(history)
        for item in items:
            if not any(existing is item for existing in merged):
                merged.append(item)
        return merged

    def attach_controller(self, controller) -> None:
        if controller in self._controllers:
            self._controller = controller
            self._sync_lists_from_controller()
            self._update_controls()
            return

        self._controllers.append(controller)
        self._controller = controller
        connections = (
            (
                controller.transferStatsChanged,
                lambda text, current=controller: self._set_status_text(text)
                if current in self._controllers
                else None,
            ),
            (
                controller.transferListsChanged,
                lambda _pending, _errors, _completed, current=controller:
                self._sync_lists_from_controller()
                if current in self._controllers
                else None,
            ),
            (
                controller.transferProgressChanged,
                lambda item, done, total, current=controller: self._set_item_progress(
                    item, done, total
                )
                if current in self._controllers
                else None,
            ),
            (
                controller.finished,
                lambda _result, current=controller: self._on_controller_finished(current),
            ),
        )
        connected: list[tuple[object, object]] = []
        try:
            for signal, slot in connections:
                signal.connect(slot)
                connected.append((signal, slot))
        except Exception:
            for signal, slot in connected:
                try:
                    signal.disconnect(slot)
                except (RuntimeError, TypeError):
                    pass
            self._controllers.remove(controller)
            self._controller = self._controllers[-1] if self._controllers else None
            self._update_controls()
            return

        self._controller_connections_by_id[id(controller)] = connected
        self._sync_lists_from_controller()
        self._update_controls()

    def _detach_controller(self, controller=None) -> None:
        targets = list(self._controllers) if controller is None else [controller]
        for target in targets:
            for signal, slot in self._controller_connections_by_id.pop(id(target), []):
                try:
                    signal.disconnect(slot)
                except (RuntimeError, TypeError):
                    pass
            try:
                self._controllers.remove(target)
            except ValueError:
                pass
        self._controller = self._controllers[-1] if self._controllers else None
        self._update_controls()

    def _on_controller_finished(self, controller) -> None:
        if controller not in self._controllers:
            return
        for item, error in list(getattr(controller, "_errors", []) or []):
            if not any(existing is item for existing, _ in self._finished_errors):
                self._finished_errors.append((item, str(error)))
        for item in list(getattr(controller, "_completed", []) or []):
            if not any(existing is item for existing in self._finished_completed):
                self._finished_completed.append(item)
        self._detach_controller(controller)
        self._sync_lists_from_controller()

    def _set_status_text(self, text: str) -> None:
        self._last_status_text = text or ""
        self.status_label.setText(self._last_status_text)
        # Progress/stat messages can arrive for every transferred chunk.  The
        # transfer-list signal handles structural changes; never rebuild the
        # bounded queue for a text-only status update.
        for index in range(self.queue_list.topLevelItemCount()):
            row = self.queue_list.topLevelItem(index)
            if row.childCount() > 0:
                row.child(0).setText(2, self._last_status_text)

    def _set_item_progress(self, item, done, total) -> None:
        try:
            total_value = int(total)
            done_value = int(done)
        except Exception:
            return
        if total_value <= 0:
            return
        percent = max(
            0,
            min(100, int(done_value * 100 / total_value)),
        )
        self._progress_by_item[id(item)] = percent
        bar = self._progress_bar_by_item_id.get(id(item))
        if bar is not None:
            bar.setValue(percent)

    def _sync_lists_from_controller(self) -> None:
        pending: list = []
        errors = list(self._finished_errors)
        completed = list(self._finished_completed)
        active_items: list = []
        for controller in self._controllers:
            pending.extend(list(getattr(controller, "_pending", []) or []))
            errors.extend(list(getattr(controller, "_errors", []) or []))
            completed.extend(list(getattr(controller, "_completed", []) or []))
            controller_active = list(getattr(controller, "_active_items", []) or [])
            legacy_active = getattr(controller, "_active_item", None)
            if not controller_active and legacy_active is not None:
                controller_active = [legacy_active]
            active_items.extend(controller_active)
        self._sync_lists(pending, errors, completed, active_items)

    def _sync_lists(self, pending, errors, completed, active_items=None) -> None:
        active_items = list(active_items or [])
        active_transfers = self._visible_transfer_items(active_items)
        pending_transfers = self._visible_transfer_items(pending)
        queue_items = active_transfers + pending_transfers
        visible_active_count = min(
            len(active_transfers),
            self._MAX_VISIBLE_TRANSFER_ROWS,
        )
        queue_rows = [
            (active, "Transferring", self._last_status_text)
            for active in active_transfers[:visible_active_count]
        ]
        remaining_slots = self._MAX_VISIBLE_TRANSFER_ROWS - visible_active_count
        queue_rows.extend(
            (item, "Queued", "")
            for item in pending_transfers[:remaining_slots]
        )
        queue_hidden = len(queue_items) - self._MAX_VISIBLE_TRANSFER_ROWS

        failed_items = [
            item
            for item, _err in errors
            if getattr(item, "op", "") in {"upload", "download"}
        ]
        failed_details = {
            id(item): str(err)
            for item, err in errors
            if getattr(item, "op", "") in {"upload", "download"}
        }
        failed_rows = [
            (item, "Failed", failed_details.get(id(item), ""))
            for item in failed_items[: self._MAX_VISIBLE_TRANSFER_ROWS]
        ]
        failed_hidden = len(failed_items) - self._MAX_VISIBLE_TRANSFER_ROWS

        completed_transfers = self._visible_transfer_items(completed)
        completed_rows = [
            (item, "Successful", "")
            for item in completed_transfers[: self._MAX_VISIBLE_TRANSFER_ROWS]
        ]
        completed_hidden = (
            len(completed_transfers) - self._MAX_VISIBLE_TRANSFER_ROWS
        )

        self._reconcile_visible_rows(self.queue_list, queue_rows, queue_hidden)
        self._reconcile_visible_rows(self.failed_list, failed_rows, failed_hidden)
        self._reconcile_visible_rows(
            self.completed_list,
            completed_rows,
            completed_hidden,
        )
        self._update_summary(queue_items)
        self._tab_counts.update(
            queue=len(queue_items),
            failed=len(failed_items),
            completed=len(completed_transfers),
        )
        self.retranslate_ui()
        self._update_controls()

    def _call_controller(self, method: str, *args) -> None:
        if method in {"cancel_all", "clear_pending"}:
            handled = False
            for controller in list(self._controllers):
                action = getattr(controller, method, None)
                if callable(action):
                    action(*args)
                    handled = True
            if handled:
                return
        action = getattr(self._controller, method, None) if self._controller else None
        if callable(action):
            action(*args)
            return
        history_actions = {
            "remove_failed_items": lambda items: self._remove_history_items(
                self.failed_list,
                items,
            ),
            "clear_failed": self.failed_list.clear,
            "remove_completed_items": lambda items: self._remove_history_items(
                self.completed_list,
                items,
            ),
            "clear_completed": self.completed_list.clear,
        }
        fallback = history_actions.get(method)
        if callable(fallback):
            fallback(*args)
            self.retranslate_ui()

    def _controller_action_available(self, method: str) -> bool:
        if self._controller is not None and callable(
            getattr(self._controller, method, None)
        ):
            return True
        return method in {
            "remove_failed_items",
            "clear_failed",
            "remove_completed_items",
            "clear_completed",
        }

    @staticmethod
    def _remove_history_items(view: QTreeWidget, items: list) -> None:
        selected_ids = {id(item) for item in items}
        for index in range(view.topLevelItemCount() - 1, -1, -1):
            row = view.topLevelItem(index)
            if id(row.data(0, Qt.ItemDataRole.UserRole)) in selected_ids:
                view.takeTopLevelItem(index)

    @staticmethod
    def _selected_transfer_items(view: QTreeWidget, *, queued_only: bool = False) -> list:
        items = []
        seen: set[int] = set()
        for row in view.selectedItems():
            if row.parent() is not None:
                row = row.parent()
            if queued_only and row.text(6) != "Queued":
                continue
            item = row.data(0, Qt.ItemDataRole.UserRole)
            if item is not None and id(item) not in seen:
                seen.add(id(item))
                items.append(item)
        return items

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.btn_stop.setEnabled(enabled)
        self.btn_cancel.setEnabled(enabled)
        self.btn_clear_pending.setEnabled(enabled)

    def _update_controls(self) -> None:
        if not self._controllers:
            self._set_controls_enabled(False)
            return
        pending = any(
            bool(getattr(controller, "_pending", []) or [])
            for controller in self._controllers
        )
        active = any(
            bool(
                getattr(controller, "_active_items", [])
                or getattr(controller, "_active_item", None)
            )
            for controller in self._controllers
        )
        running = any(
            bool(getattr(controller, "_running", False))
            for controller in self._controllers
        )
        self.btn_stop.setEnabled(running or active or pending)
        self.btn_cancel.setEnabled(running or active or pending)
        self.btn_clear_pending.setEnabled(pending)


__all__ = [
    "ActivitySyncMixin",
]
