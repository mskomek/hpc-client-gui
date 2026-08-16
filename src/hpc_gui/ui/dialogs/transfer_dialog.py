from __future__ import annotations

import inspect
import time
from threading import Thread
from typing import Callable, List

from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from hpc_gui.core.i18n import t
from hpc_gui.core.debug_telemetry import is_source_run
from hpc_gui.core.logging import get_logger
from hpc_gui.services.transfer_controller import TransferController, TransferItem


def _tr(key: str, fallback: str) -> str:
    value = t(key)
    return fallback if value == f"[{key}]" else value


class TransferPreflightDialog(QDialog):
    """Read-only upload plan shown before any transfer worker starts."""

    _MAX_PLAN_ROWS = 200

    def __init__(
        self,
        parent=None,
        *,
        title: str,
        items: List[TransferItem],
        parallel_limit: int,
    ) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle(
            _tr("transfer.preflight_title", "Confirm upload plan")
        )
        self._items = list(items)

        file_count = sum(item.op == "upload" for item in self._items)
        folder_count = sum(item.op == "mkdir_remote" for item in self._items)
        self.lbl_summary = QLabel(
            _tr(
                "transfer.preflight_summary",
                "{files} files, {folders} folder steps, {steps} total steps. "
                "Up to {parallel} transfers will run at once.",
            ).format(
                files=file_count,
                folders=folder_count,
                steps=len(self._items),
                parallel=parallel_limit,
            )
        )
        self.lbl_summary.setWordWrap(True)

        self.plan_list = QTreeWidget()
        self.plan_list.setColumnCount(3)
        self.plan_list.setHeaderLabels(
            [
                _tr("transfer.preflight_operation", "Operation"),
                _tr("transfer.preflight_source", "Source"),
                _tr("transfer.preflight_destination", "Destination"),
            ]
        )
        operation_labels = {
            "upload": _tr("transfer.preflight_upload", "Upload"),
            "mkdir_remote": _tr("transfer.preflight_create_folder", "Create folder"),
            "delete": _tr("transfer.preflight_delete", "Delete existing"),
        }
        for item in self._items[: self._MAX_PLAN_ROWS]:
            QTreeWidgetItem(
                self.plan_list,
                [
                    operation_labels.get(item.op, item.op),
                    item.src or "—",
                    item.dst or "—",
                ],
            )
        hidden = len(self._items) - self._MAX_PLAN_ROWS
        if hidden > 0:
            QTreeWidgetItem(self.plan_list, [f"Remaining: {hidden}", "", ""])
        self.plan_list.resizeColumnToContents(0)
        self.plan_list.resizeColumnToContents(1)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.btn_start = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.btn_cancel = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        self.btn_start.setText(_tr("transfer.preflight_start", "Start transfer"))
        self.btn_cancel.setText(_tr("common.cancel", "Cancel"))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.cb_dont_ask_again = QCheckBox(
            _tr("transfer.preflight_dont_ask_again", "Don't ask again")
        )

        root = QVBoxLayout(self)
        root.addWidget(QLabel(title))
        root.addWidget(self.lbl_summary)
        root.addWidget(self.plan_list)
        bottom_row = QHBoxLayout()
        bottom_row.addWidget(self.cb_dont_ask_again)
        bottom_row.addStretch(1)
        bottom_row.addWidget(self.buttons)
        root.addLayout(bottom_row)
        self.resize(850, 480)


class _TransferWorker(QObject):
    progress = Signal(int, object)
    finished = Signal(object, bool, str)

    def __init__(self, items: List[TransferItem], run_item: Callable[[TransferItem], None]):
        super().__init__()
        self._items = list(items)
        self._run_item = run_item
        self._cancel = False

    @Slot()
    def cancel(self) -> None:
        self._cancel = True

    @Slot()
    def run(self) -> None:
        total = len(self._items)
        for idx, item in enumerate(self._items, start=1):
            if self._cancel:
                self.finished.emit(item, True, t("dirs.cancelled") if t("dirs.cancelled") != "[dirs.cancelled]" else "Cancelled.")
                return
            self.progress.emit(idx, item)
            try:
                self._run_item(item)
            except Exception as exc:
                self.finished.emit(item, False, str(exc))
                return
        self.finished.emit(None, False, "")


class TransferDialog(QDialog):
    _MAX_VISIBLE_LIST_ITEMS = 500
    _MAX_HISTORY = 1000
    _PROGRESS_PUBLISH_INTERVAL_MS = 150

    transferStatsChanged = Signal(str)
    transferListsChanged = Signal(object, object, object)
    transferProgressChanged = Signal(object, object, object)

    def __init__(
        self,
        parent=None,
        *,
        title: str,
        items: List[TransferItem],
        run_item: Callable[[TransferItem], None],
        parallel_limit: int = 1,
        max_parallel_limit: int = 10,
    ) -> None:
        super().__init__(parent)
        self.setModal(False)
        self.setWindowTitle(title or t("dirs.progress_title"))
        self._run_item = run_item
        try:
            self._run_item_accepts_progress = (
                len(inspect.signature(run_item).parameters) >= 2
            )
        except (TypeError, ValueError):
            self._run_item_accepts_progress = False
        self._max_parallel_limit = max(1, min(10, int(max_parallel_limit or 1)))
        self._parallel_limit = 1
        self.set_parallel_limit(parallel_limit)
        self._items: List[TransferItem] = list(items)
        self._pending: List[TransferItem] = list(items)
        self._completed: List[TransferItem] = []
        self._errors: List[tuple[TransferItem, str]] = []
        self._running = False
        self._finished_cleanly = False
        self._stopped = False
        self._cancelled = False
        self._started_at_by_item: dict[int, float] = {}
        self._last_progress_by_item: dict[int, tuple[int, float]] = {}
        self._last_published_at_by_item: dict[int, float] = {}
        self._item_progress_baselines: dict[int, tuple[float, float]] = {}  # item_id -> (done, time)
        self._active_item: TransferItem | None = None
        self._active_items: List[TransferItem] = []

        self.lbl_status = QLabel(self._status_text())
        self.lbl_transfer_stats = QLabel(_tr("transfer.no_active_transfer", "No active transfer."))

        self.tabs = QTabWidget()
        self.queue_list = QListWidget()
        self.errors_list = QListWidget()
        self.completed_list = QListWidget()
        self.tabs.addTab(self.queue_list, t("transfer.queue_tab"))
        self.tabs.addTab(self.errors_list, t("transfer.errors_tab"))
        self.tabs.addTab(self.completed_list, t("transfer.completed_tab"))

        self.queue_list.setMinimumHeight(140)
        self.errors_list.setMinimumHeight(140)
        self.completed_list.setMinimumHeight(140)
        self.errors_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.errors_list.customContextMenuRequested.connect(self._show_errors_menu)

        self.btn_stop = QPushButton(t("transfer.stop"))
        self.btn_cancel = QPushButton(t("transfer.cancel"))
        self.btn_clear_pending = QPushButton(_tr("transfer.clear_pending", "Clear queued"))
        self.btn_retry = QPushButton(t("transfer.retry_failed"))
        self.btn_close = QPushButton(t("common.close"))
        self.btn_stop.clicked.connect(self.cancel_all)
        self.btn_cancel.clicked.connect(self.cancel_all)
        self.btn_clear_pending.clicked.connect(self.clear_pending)
        self.btn_retry.clicked.connect(self.retry_selected_errors)
        self.btn_close.clicked.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_stop)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_clear_pending)
        btn_row.addWidget(self.btn_retry)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_close)

        root = QVBoxLayout(self)
        root.addWidget(self.lbl_status)
        root.addWidget(self.lbl_transfer_stats)
        self.lbl_parallel_hint = QLabel(
            _tr(
                "transfer.parallel_hint",
                "Configured parallel transfer limit: {limit}",
            ).format(limit=self._parallel_limit)
        )
        root.addWidget(self.lbl_parallel_hint)
        root.addWidget(self.tabs)
        root.addLayout(btn_row)

        self._thread = None
        self._worker = None
        self._worker_state = {"cancelled": False, "error": ""}
        self._refresh_scheduled = False
        self._close_when_done = False
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(50)
        self._refresh_timer.timeout.connect(self._run_scheduled_refresh)

    def set_parallel_limit(self, parallel_limit: int) -> int:
        """Set queue concurrency without exceeding the backend-safe cap."""
        requested = max(1, min(10, int(parallel_limit or 1)))
        self._parallel_limit = min(requested, self._max_parallel_limit)
        if hasattr(self, "lbl_parallel_hint"):
            self.lbl_parallel_hint.setText(
                _tr(
                    "transfer.parallel_hint",
                    "Configured parallel transfer limit: {limit}",
                ).format(limit=self._parallel_limit)
            )
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
            view.addItem(f"Remaining: {hidden}")

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

    def start(self) -> None:
        if self._running or self._active_items or self._active_item is not None:
            return
        if not self._items:
            self._finished_cleanly = True
            self.accept()
            return
        self._schedule_refresh()
        if is_source_run():
            get_logger("hpc_gui.debug.transfer").info(
                "transfer.queue started title=%r item_count=%d parallel_limit=%d",
                self.windowTitle(), len(self._items), self._parallel_limit,
            )
        self._thread = _WorkerThread(
            self._pending,
            self._execute_item,
            parallel_limit=self._parallel_limit,
        )
        self._thread.item_started.connect(self._on_item_started)
        self._thread.item_finished.connect(self._on_item_finished)
        self._thread.transfer_progress.connect(self._on_transfer_progress)
        self._thread.all_done.connect(self._on_all_done)
        self._thread.start()
        self._running = True

    def is_active(self) -> bool:
        """Return whether this dialog can accept more queued work."""
        return self._running and not self._cancelled and not self._stopped

    def enqueue(self, items: List[TransferItem]) -> bool:
        """Append items to the existing worker queue without starting a second worker."""
        if not items or not self.is_active() or self._thread is None:
            return False
        if not self._thread.enqueue(items):
            return False
        self._items.extend(items)
        self._pending.extend(items)
        self._schedule_refresh()
        return True

    def _execute_item(self, item: TransferItem, progress_cb=None) -> None:
        if self._run_item_accepts_progress:
            self._run_item(item, progress_cb)
        else:
            self._run_item(item)

    @Slot(int, object)
    def _on_item_started(self, _index: int, item: TransferItem) -> None:
        if id(item) not in self._started_at_by_item:
            self._started_at_by_item[id(item)] = time.monotonic()
        if item not in self._active_items:
            self._active_items.append(item)
        self._active_item = self._active_items[0] if self._active_items else item
        text = _tr("transfer.active_item", "Running: {item}").format(item=item.label())
        self.lbl_transfer_stats.setText(text)
        self.transferStatsChanged.emit(text)
        try:
            self._pending.remove(item)
        except ValueError:
            pass
        self._schedule_refresh()
        if is_source_run():
            get_logger("hpc_gui.debug.transfer").info(
                "transfer.item started operation=%s source=%r destination=%r recursive=%s",
                item.op, item.src, item.dst, item.recursive,
            )

    @Slot(object, bool, str)
    def _on_item_finished(self, item: TransferItem, cancelled: bool, error: str) -> None:
        if item is None:
            return
        started = self._started_at_by_item.pop(id(item), None)
        self._item_progress_baselines.pop(id(item), None)
        progress = self._last_progress_by_item.pop(id(item), None)
        if is_source_run():
            elapsed_ms = int((time.monotonic() - started) * 1000) if started is not None else -1
            bytes_done = progress[0] if progress is not None else 0
            avg_speed = bytes_done / (elapsed_ms / 1000) if elapsed_ms > 0 else 0.0
            get_logger("hpc_gui.debug.transfer").info(
                "transfer.item finished operation=%s source=%r destination=%r status=%s bytes=%d average_speed_Bps=%.1f duration_ms=%d error=%r",
                item.op, item.src, item.dst,
                "cancelled" if cancelled else ("failed" if error else "completed"),
                bytes_done, avg_speed, elapsed_ms, error,
            )
        # Every outcome must fall through to the shared cleanup below: leaving
        # a cancelled item in `_active_items` keeps its "Running: ..." row on
        # screen forever and makes start()/process_queue() refuse to run again.
        if cancelled:
            self._pending.clear()
            self._running = False
            # Park it with the failures so the existing retry path can restart
            # it; a cancelled transfer that lands in no list at all cannot be
            # resumed by any means.
            self._errors.append(
                (item, _tr("transfer.cancelled", "Transfer cancelled."))
            )
        elif error:
            self._errors.append((item, error))
        else:
            self._completed.append(item)
            if len(self._completed) > self._MAX_HISTORY:
                del self._completed[:-self._MAX_HISTORY]
        try:
            self._active_items.remove(item)
        except ValueError:
            pass
        self._active_item = self._active_items[0] if self._active_items else None
        self._schedule_refresh()

    @Slot(object, object, object)
    def _on_transfer_progress(self, item: TransferItem, done: int, total: int) -> None:
        now = time.monotonic()
        item_id = id(item)
        done = int(done)
        total = int(total)
        baseline = self._item_progress_baselines.get(item_id)
        if baseline is None:
            self._item_progress_baselines[item_id] = (float(done), now)
            speed = 0.0
        else:
            baseline_done, baseline_time = baseline
            elapsed = max(0.001, now - baseline_time)
            speed = max(0.0, float(done - baseline_done) / elapsed) if done > baseline_done else 0.0

        self._last_progress_by_item[item_id] = (done, now)
        published_at = self._last_published_at_by_item.get(item_id)
        if not (
            total > 0 and done >= total
        ) and published_at is not None and (now - published_at) * 1000 < self._PROGRESS_PUBLISH_INTERVAL_MS:
            return
        self._last_published_at_by_item[item_id] = now
        remaining = max(0, total - done) if total else 0
        eta = remaining / speed if speed > 0 and total else 0

        text = _tr(
            "transfer.progress_detail",
            "{item} — {done}/{total}, {speed}, remaining {eta}",
        ).format(
            item=item.label(),
            done=_format_size(done),
            total=_format_size(total) if total else "?",
            speed=f"{_format_size(speed)}/s",
            eta=_format_duration(eta) if total else "?",
        )
        self.lbl_transfer_stats.setText(text)
        self.transferStatsChanged.emit(text)
        self.transferProgressChanged.emit(item, done, total)

    @Slot()
    def _on_all_done(self) -> None:
        self._running = False
        self._refresh_timer.stop()
        self._refresh()
        if is_source_run():
            get_logger("hpc_gui.debug.transfer").info(
                "transfer.queue finished title=%r completed=%d failed=%d pending=%d stopped=%s cancelled=%s",
                self.windowTitle(), len(self._completed), len(self._errors),
                len(self._pending), self._stopped, self._cancelled,
            )
        if self._stopped and self._pending:
            text = _tr("transfer.stopped_after_current", "Stopped after the current transfer.")
            self.lbl_transfer_stats.setText(text)
            self.transferStatsChanged.emit(text)
            if self._close_when_done:
                super().reject()
            return
        if self._cancelled:
            text = _tr("transfer.cancelled", "Transfer cancelled.")
            self.lbl_transfer_stats.setText(text)
            self.transferStatsChanged.emit(text)
            if self._close_when_done:
                super().reject()
            return
        if self._close_when_done:
            super().reject()
            return
        if not self._errors and not self._stopped and not self._cancelled and not self._pending:
            self._finished_cleanly = True
            if self._close_when_done:
                super().reject()
            else:
                self.accept()

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
            (item, error)
            for item, error in self._errors
            if id(item) not in selected_ids
        ]
        self._refresh()
        return before - len(self._errors)

    def clear_failed(self) -> None:
        self._errors.clear()
        self._refresh()

    def remove_completed_items(self, items: List[TransferItem]) -> int:
        selected_ids = {id(item) for item in items}
        before = len(self._completed)
        self._completed = [
            item for item in self._completed if id(item) not in selected_ids
        ]
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
        super().reject()


class _WorkerThread(QObject):
    item_started = Signal(int, object)
    item_finished = Signal(object, bool, str)
    transfer_progress = Signal(object, object, object)
    all_done = Signal()

    def __init__(self, items, run_item, *, parallel_limit=1):
        super().__init__()
        self._items = list(items)
        self._controller = TransferController(
            items,
            run_item,
            parallel_limit=parallel_limit,
            on_queue=self._queue_event,
            on_progress=lambda item, done, total: self.transfer_progress.emit(item, done, total),
        )
        self._start_index = 0

    def start(self) -> None:
        self._controller.start()
        Thread(target=self._wait_for_done, daemon=True).start()

    def enqueue(self, items) -> bool:
        return self._controller.enqueue(items)

    def _wait_for_done(self) -> None:
        self._controller.wait()
        try:
            self.all_done.emit()
        except RuntimeError:
            # The dialog was closed while the queue drained; there is nobody
            # left to notify, and letting this escape logs a bogus crash.
            pass

    def _queue_event(self, event: str, item: TransferItem) -> None:
        if event == "started":
            self._start_index += 1
            self.item_started.emit(self._start_index, item)
        elif event == "completed":
            self.item_finished.emit(item, False, "")
        elif event == "failed":
            error = next((message for failed, message in self._controller.failed if failed is item), "Transfer failed")
            self.item_finished.emit(item, error == "cancelled", "" if error == "cancelled" else error)

    def stop_after_current(self) -> None:
        self._controller.stop_after_current()

    def cancel_all(self) -> None:
        self._controller.cancel_all()

    def clear_pending(self) -> None:
        self._controller.clear_pending()

    def remove_pending_items(self, items) -> None:
        self._controller.remove_pending_items(items)

    def set_pending_priorities(self, items, priority: str) -> None:
        self._controller.set_pending_priorities(items, priority)
def _format_size(value: float) -> str:
    try:
        amount = float(value)
    except Exception:
        amount = 0.0
    units = ["B", "KB", "MB", "GB", "TB"]
    index = 0
    while amount >= 1024 and index < len(units) - 1:
        amount /= 1024.0
        index += 1
    return f"{amount:.1f} {units[index]}" if index else f"{int(amount)} {units[index]}"


def _format_duration(seconds: float) -> str:
    try:
        remaining = max(0, int(seconds))
    except Exception:
        remaining = 0
    minutes, secs = divmod(remaining, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


class _TransferCancelled(Exception):
    pass
