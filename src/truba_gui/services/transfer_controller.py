from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from threading import Event, Lock, Thread
from typing import Callable, Iterable
from collections import deque


@dataclass
class TransferItem:
    op: str
    src: str
    dst: str
    recursive: bool = False
    priority: str = "Normal"
    cached_size: int | None = None

    def label(self) -> str:
        name = (self.dst or self.src).rstrip("/").split("/")[-1]
        return f"{self.op}: {name or (self.dst or self.src)}"


class TransferCancelled(Exception):
    pass


class TransferController:
    """Headless transfer queue; UI layers subscribe through callbacks."""

    def __init__(
        self,
        items: Iterable[TransferItem],
        run_item: Callable[[TransferItem, Callable[[int, int], None]], None],
        *,
        parallel_limit: int = 1,
        history_limit: int = 1000,
        on_queue: Callable[[str, TransferItem], None] | None = None,
        on_progress: Callable[[TransferItem, int, int], None] | None = None,
    ) -> None:
        self.items = self._normalize(list(items))
        self._run_item = run_item
        self.parallel_limit = max(1, min(10, int(parallel_limit or 1)))
        self._pending = list(self.items)
        self._failed: list[tuple[TransferItem, str]] = []
        self._completed: deque[TransferItem] = deque(maxlen=max(1, history_limit))
        self._on_queue = on_queue
        self._on_progress = on_progress
        self._cancel = Event()
        self._stop_after_current = Event()
        self._lock = Lock()
        self._thread: Thread | None = None
        self._done = Event()

    @staticmethod
    def _normalize(items: list[TransferItem]) -> list[TransferItem]:
        allowed = {"mkdir_remote", "mkdir_local", "upload", "download"}
        if items and all(item.op in allowed for item in items):
            mkdirs = [item for item in items if item.op in {"mkdir_remote", "mkdir_local"}]
            transfers = [item for item in items if item.op in {"upload", "download"}]
            return mkdirs + transfers if mkdirs and transfers else items
        return items
    @property
    def pending(self) -> list[TransferItem]:
        with self._lock:
            return list(self._pending)

    @property
    def failed(self) -> list[tuple[TransferItem, str]]:
        with self._lock:
            return list(self._failed)

    @property
    def completed(self) -> list[TransferItem]:
        with self._lock:
            return list(self._completed)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._done.clear()
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

    def wait(self, timeout: float | None = None) -> bool:
        return self._done.wait(timeout)

    def cancel_all(self) -> None:
        self._cancel.set()
        self._stop_after_current.set()

    def stop_after_current(self) -> None:
        self._stop_after_current.set()

    def retry_failed(self) -> int:
        with self._lock:
            restored = [item for item, _error in self._failed]
            self._failed.clear()
            self._pending = restored + self._pending
            self.items = list(self._pending)
        self._cancel.clear()
        self._stop_after_current.clear()
        return len(restored)

    def clear_pending(self) -> None:
        self._stop_after_current.set()
        with self._lock:
            self._pending.clear()

    def remove_pending_items(self, items: Iterable[TransferItem]) -> int:
        selected = {id(item) for item in items}
        with self._lock:
            before = len(self._pending)
            self._pending = [item for item in self._pending if id(item) not in selected]
            return before - len(self._pending)

    def set_pending_priorities(self, items: Iterable[TransferItem], priority: str) -> None:
        selected = {id(item) for item in items}
        with self._lock:
            for item in self._pending:
                if id(item) in selected:
                    item.priority = priority
    def _start_item(self, item: TransferItem) -> None:
        with self._lock:
            if item in self._pending:
                self._pending.remove(item)
        self._emit_queue("started", item)

    def _finish_item(self, item: TransferItem, error: str | None) -> None:
        if error is None:
            with self._lock:
                self._completed.append(item)
            self._emit_queue("completed", item)
        else:
            with self._lock:
                self._failed.append((item, error))
            self._emit_queue("failed", item)
    def _emit_queue(self, event: str, item: TransferItem) -> None:
        if self._on_queue:
            self._on_queue(event, item)

    def _one(self, item: TransferItem) -> tuple[TransferItem, str | None]:
        try:
            def progress(done: int, total: int) -> None:
                if self._cancel.is_set():
                    raise TransferCancelled()
                if self._on_progress:
                    self._on_progress(item, int(done), int(total))
            self._run_item(item, progress)
            return item, None
        except TransferCancelled:
            return item, "cancelled"
        except Exception as exc:
            return item, str(exc)

    def _run(self) -> None:
        next_index = 0
        try:
            with ThreadPoolExecutor(max_workers=self.parallel_limit) as executor:
                while next_index < len(self.items):
                    if self._cancel.is_set():
                        break
                    item = self.items[next_index]
                    if item.op not in {"upload", "download"}:
                        next_index += 1
                        self._start_item(item)
                        result, error = self._one(item)
                        self._finish_item(result, error)
                        if error == "cancelled":
                            break
                        continue
                    batch = []
                    force_single = next_index > 0 and self.items[next_index - 1].op in {"delete", "delete_local"}
                    while (
                        next_index < len(self.items)
                        and len(batch) < (1 if force_single else self.parallel_limit)
                        and not self._stop_after_current.is_set()
                        and self.items[next_index].op in {"upload", "download"}
                    ):
                        item = self.items[next_index]
                        next_index += 1
                        batch.append(item)
                        self._start_item(item)
                    futures = {executor.submit(self._one, item): item for item in batch}
                    while futures:
                        done, _ = wait(futures, return_when=FIRST_COMPLETED)
                        for future in done:
                            item = futures.pop(future)
                            result, error = future.result()
                            self._finish_item(result, error)
                            if error == "cancelled":
                                self._cancel.set()
                        if self._cancel.is_set():
                            break
        finally:
            self._done.set()
            for item in self.pending:
                self._emit_queue("queued", item)