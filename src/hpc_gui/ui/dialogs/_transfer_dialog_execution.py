from __future__ import annotations

import time
from typing import List

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QDialog

from hpc_gui.core.debug_telemetry import is_source_run
from hpc_gui.core.logging import get_logger
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.ui.dialogs._transfer_dialog_support import (
    _WorkerThread,
    _format_duration,
    _format_size,
    _tr,
)


class _TransferDialogExecution:
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
                self.windowTitle(),
                len(self._items),
                self._parallel_limit,
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
        if factory is not None and item.op in {"upload", "download"}:
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
                item.op,
                item.src,
                item.dst,
                item.recursive,
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
                item.op,
                item.src,
                item.dst,
                "cancelled" if cancelled else ("failed" if error else "completed"),
                bytes_done,
                avg_speed,
                elapsed_ms,
                error,
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
            self._errors.append((item, _tr("transfer.cancelled", "Transfer cancelled.")))
        elif error:
            self._errors.append((item, error))
        else:
            self._completed.append(item)
            if len(self._completed) > self._MAX_HISTORY:
                del self._completed[: -self._MAX_HISTORY]
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
        if (
            not (total > 0 and done >= total)
            and published_at is not None
            and (now - published_at) * 1000 < self._PROGRESS_PUBLISH_INTERVAL_MS
        ):
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
                self.windowTitle(),
                len(self._completed),
                len(self._errors),
                len(self._pending),
                self._stopped,
                self._cancelled,
            )
        self.queueFinished.emit()
        if self._stopped and self._pending:
            text = _tr("transfer.stopped_after_current", "Stopped after the current transfer.")
            self.lbl_transfer_stats.setText(text)
            self.transferStatsChanged.emit(text)
            if self._close_when_done:
                QDialog.reject(self)
            return
        if self._cancelled:
            text = _tr("transfer.cancelled", "Transfer cancelled.")
            self.lbl_transfer_stats.setText(text)
            self.transferStatsChanged.emit(text)
            if self._close_when_done:
                QDialog.reject(self)
            return
        if self._close_when_done:
            QDialog.reject(self)
            return
        if not self._errors and not self._stopped and not self._cancelled and not self._pending:
            self._finished_cleanly = True
            if self._close_when_done:
                QDialog.reject(self)
            else:
                self.accept()
