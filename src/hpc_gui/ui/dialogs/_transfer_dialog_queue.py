from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu
from PySide6.QtWidgets import QDialog

from hpc_gui.core.i18n import t
from hpc_gui.services.transfer_controller import TransferItem


class _TransferDialogQueue:
    def _show_errors_menu(self, pos) -> None:
        item = self.errors_list.itemAt(pos)
        if item is not None:
            self.errors_list.setCurrentItem(item)
        if not self.errors_list.selectedItems():
            return
        menu = QMenu(self)
        act_retry = menu.addAction(t("transfer.retry_selected"))
        chosen = menu.exec(self.errors_list.mapToGlobal(pos))
        if chosen == act_retry:
            self.retry_selected_errors()

    def retry_selected_errors(self) -> None:
        selected = self.errors_list.selectedItems()
        selected_items = [
            lw.data(Qt.ItemDataRole.UserRole)
            for lw in selected
            if lw.data(Qt.ItemDataRole.UserRole) is not None
        ]
        self.retry_failed_items(selected_items)

    def retry_failed_items(self, items: List[TransferItem]) -> int:
        selected_ids = {id(item) for item in items}
        if not selected_ids:
            return 0
        restored: List[TransferItem] = []
        remaining: List[tuple[TransferItem, str]] = []
        for item, err in self._errors:
            if id(item) in selected_ids:
                restored.append(item)
            else:
                remaining.append((item, err))
        if not restored:
            return 0
        self._errors = remaining
        self._pending = restored + self._pending
        self._refresh()
        if not self._running:
            self.start()
        return len(restored)

    def retry_all_errors(self) -> int:
        return self.retry_failed_items([item for item, _err in self._errors])

    def process_queue(self) -> bool:
        """Start paused queued work, without creating a duplicate worker."""
        if self._running or self._active_items or self._active_item is not None:
            return False
        if not self._pending:
            return False
        self._stopped = False
        self._cancelled = False
        self._finished_cleanly = False
        self.start()
        return True

    def set_pending_priority(self, items: List[TransferItem], priority: str) -> int:
        """Apply a stable priority order to queued transfer items only."""
        priorities = ("Highest", "High", "Normal", "Low", "Lowest")
        if priority not in priorities:
            return 0
        selected_ids = {id(item) for item in items}
        changed = 0
        for item in self._pending:
            if id(item) in selected_ids:
                item.priority = priority
                changed += 1
        order = {name: index for index, name in enumerate(priorities)}
        self._pending.sort(key=lambda item: order.get(getattr(item, "priority", "Normal"), 2))
        if self._thread is not None:
            self._thread.set_pending_priorities(items, priority)
        self._refresh()
        return changed

    def remove_pending_items(self, items: List[TransferItem]) -> int:
        selected_ids = {id(item) for item in items}
        removed = [item for item in self._pending if id(item) in selected_ids]
        if not removed:
            return 0
        if self._thread is not None:
            self._thread.remove_pending_items(removed)
        self._pending = [item for item in self._pending if id(item) not in selected_ids]
        self._refresh()
        return len(removed)

    def remove_failed_items(self, items: List[TransferItem]) -> int:
        selected_ids = {id(item) for item in items}
        before = len(self._errors)
        self._errors = [
            (item, error) for item, error in self._errors if id(item) not in selected_ids
        ]
        self._refresh()
        return before - len(self._errors)

    def clear_failed(self) -> None:
        self._errors.clear()
        self._refresh()

    def remove_completed_items(self, items: List[TransferItem]) -> int:
        selected_ids = {id(item) for item in items}
        before = len(self._completed)
        self._completed = [item for item in self._completed if id(item) not in selected_ids]
        self._refresh()
        return before - len(self._completed)

    def clear_completed(self) -> None:
        self._completed.clear()
        self._refresh()

    def stop_after_current(self) -> None:
        self._stopped = True
        if self._thread is not None:
            self._thread.stop_after_current()

    def cancel_all(self) -> None:
        self._cancelled = True
        if self._thread is not None:
            self._thread.cancel_all()
        self._pending.clear()
        self._refresh()

    def clear_pending(self) -> None:
        self._stopped = True
        if self._thread is not None:
            self._thread.clear_pending()
        self._pending.clear()
        self._refresh()

    def finished_cleanly(self) -> bool:
        return self._finished_cleanly and not self._errors

    def reject(self) -> None:  # type: ignore[override]
        self.cancel_all()
        if self._running or self._active_items or self._active_item is not None:
            # Keep the QObject alive until the worker has emitted all_done.
            # The owner will delete the dialog from its finished callback.
            self._close_when_done = True
            return
        QDialog.reject(self)
