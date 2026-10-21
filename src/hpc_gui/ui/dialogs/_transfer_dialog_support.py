from __future__ import annotations

from threading import Thread

from PySide6.QtCore import QObject, Signal

from hpc_gui.core.i18n import t
from hpc_gui.services.transfer_controller import TransferController, TransferItem


def _tr(key: str, fallback: str) -> str:
    value = t(key)
    return fallback if value == f"[{key}]" else value


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
            error = next(
                (message for failed, message in self._controller.failed if failed is item),
                "Transfer failed",
            )
            self._emit(
                self.item_finished,
                item,
                error == "cancelled",
                "" if error == "cancelled" else error,
            )

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
