from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget, QListWidgetItem

from hpc_gui.core.i18n import t
from hpc_gui.ui.dialogs._transfer_dialog_support import _tr


class _TransferDialogViews:
    def _parallel_hint_text(self) -> str:
        configured = self._configured_limit
        effective = self._parallel_limit
        if configured is not None and configured != effective:
            reason = (
                t("transfer.parallel_reduced_backend")
                if self._max_parallel_limit <= 1
                else t("transfer.parallel_reduced_server")
            )
            return _tr(
                "transfer.parallel_hint_pair",
                "Configured limit: {configured} · Effective limit for this connection: {effective} ({reason})",
            ).format(configured=configured, effective=effective, reason=reason)
        if configured is not None:
            return _tr(
                "transfer.parallel_hint_effective",
                "Configured limit: {configured} · Effective limit for this connection: {effective}",
            ).format(configured=configured, effective=effective)
        return _tr(
            "transfer.parallel_hint",
            "Configured parallel transfer limit: {limit}",
        ).format(limit=effective)

    def set_parallel_limit(self, parallel_limit: int) -> int:
        """Set queue concurrency without exceeding the backend-safe cap."""
        requested = max(1, min(10, int(parallel_limit or 1)))
        self._parallel_limit = min(requested, self._max_parallel_limit)
        if hasattr(self, "lbl_parallel_hint"):
            self.lbl_parallel_hint.setText(self._parallel_hint_text())
        return self._parallel_limit

    def _status_text(self) -> str:
        return t("transfer.status").format(
            pending=len(self._pending),
            errors=len(self._errors),
            completed=len(self._completed),
        )

    def _refresh(self) -> None:
        self.lbl_status.setText(self._status_text())
        self.queue_list.clear()
        for item in self._pending[: self._MAX_VISIBLE_LIST_ITEMS]:
            self.queue_list.addItem(item.label())
        self._append_hidden_count(self.queue_list, len(self._pending))
        self.errors_list.clear()
        for item, err in self._errors[: self._MAX_VISIBLE_LIST_ITEMS]:
            lw = QListWidgetItem(f"{item.label()} — {err}")
            lw.setData(Qt.ItemDataRole.UserRole, item)
            self.errors_list.addItem(lw)
        self._append_hidden_count(self.errors_list, len(self._errors))
        self.completed_list.clear()
        for item in self._completed[: self._MAX_VISIBLE_LIST_ITEMS]:
            self.completed_list.addItem(item.label())
        self._append_hidden_count(self.completed_list, len(self._completed))
        self.btn_clear_pending.setEnabled(bool(self._pending))
        self.transferListsChanged.emit(
            list(self._pending),
            list(self._errors),
            list(self._completed),
        )

    def _append_hidden_count(self, view: QListWidget, total: int) -> None:
        hidden = total - self._MAX_VISIBLE_LIST_ITEMS
        if hidden > 0:
            view.addItem(t("transfer.remaining").format(hidden=hidden))

    def _schedule_refresh(self) -> None:
        """Coalesce worker bursts into one bounded GUI update."""
        if self._refresh_scheduled:
            return
        self._refresh_scheduled = True
        # The timer belongs to this dialog. A process-global singleShot can
        # invoke a bound method after the dialog has been deleted, which is
        # especially dangerous for remote->local downloads in frozen Qt builds.
        self._refresh_timer.start()

    def _run_scheduled_refresh(self) -> None:
        self._refresh_scheduled = False
        self._refresh()
