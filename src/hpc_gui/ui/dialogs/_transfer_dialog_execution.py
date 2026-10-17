from __future__ import annotations

import time
from threading import Thread
from typing import List

from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QListWidget, QListWidgetItem,
)
from hpc_gui.core.i18n import t
from hpc_gui.core.debug_telemetry import is_source_run
from hpc_gui.core.logging import get_logger
from hpc_gui.services.transfer_controller import TransferController, TransferItem

logger = get_logger(__name__)

def _tr(key: str, fallback: str) -> str:
    value = t(key)
    return fallback if value == f"[{key}]" else value

class _TransferDialogExecutionMixin:
    def _parallel_hint_text(self) -> str:
        configured = self._configured_limit
        effective = self._parallel_limit
        if configured is not None and configured != effective:
            reason = (
                t("transfer.parallel_reduced_backend")
                if self._max_parallel_limit <= 1
                else t("transfer.parallel_reduced_server")
            )
            return (
                _tr(
                    "transfer.parallel_hint_pair",
                    "Configured limit: {configured} · Effective limit for this connection: {effective} ({reason})",
                ).format(configured=configured, effective=effective, reason=reason)
            )
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
        factory = self._backend_context_factory
        if (
            factory is not None
            and item.op in {"upload", "download"}
        ):
            # Parallel-safe backends: run this transfer against an isolated,
            # per-thread connection and always close it afterwards.
            try:
                backend = factory()
            except Exception:
                backend = None
            if backend is not None:
                try:
                    self._invoke_run_item(item, progress_cb, files=backend)
                    return
                finally:
                    close = getattr(backend, "close", None)
                    if callable(close):
                        try:
                            close()
                        except Exception:
                            pass
        self._invoke_run_item(item, progress_cb)


    def _invoke_run_item(self, item: TransferItem, progress_cb=None, files=None) -> None:
        if files is not None:
            self._run_item(item, progress_cb, files=files)
        elif self._run_item_accepts_progress:
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
            on_progress=lambda item, done, total: self._emit(
                self.transfer_progress, item, done, total
            ),
        )
        self._start_index = 0

    def start(self) -> None:
        self._controller.start()
        Thread(target=self._wait_for_done, daemon=True).start()

    def enqueue(self, items) -> bool:
        return self._controller.enqueue(items)

    def _emit(self, signal, *args) -> None:
        # Worker threads keep reporting while a cancelled dialog is being
        # deleted by its owner. Emitting into the deleted QObject raises
        # RuntimeError at best and crashes the interpreter at worst, and
        # there is nobody left to notify either way.
        try:
            signal.emit(*args)
        except RuntimeError:
            pass

    def _wait_for_done(self) -> None:
        self._controller.wait()
        self._emit(self.all_done)

    def _queue_event(self, event: str, item: TransferItem) -> None:
        if event == "started":
            self._start_index += 1
            self._emit(self.item_started, self._start_index, item)
        elif event == "completed":
            self._emit(self.item_finished, item, False, "")
        elif event == "failed":
            error = next((message for failed, message in self._controller.failed if failed is item), "Transfer failed")
            self._emit(self.item_finished, item, error == "cancelled", "" if error == "cancelled" else error)

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

