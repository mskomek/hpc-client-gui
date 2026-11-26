from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from threading import Event, Lock, Thread
from typing import Callable, Iterable
from collections import deque
import os.path
import posixpath


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


TRANSFER_PRIORITIES = ("Highest", "High", "Normal", "Low", "Lowest")


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
        on_start: Callable[[], None] | None = None,
        on_done: Callable[[], None] | None = None,
    ) -> None:
        self.items = self._normalize(list(items))
        self._run_item = run_item
        self.parallel_limit = max(1, min(10, int(parallel_limit or 1)))
        self._pending = list(self.items)
        self._failed: list[tuple[TransferItem, str]] = []
        # Failed directory prerequisites remain blocked across retries, even if
        # their failure rows have been removed from the visible history.
        self._failed_directories: set[tuple[str, str]] = set()
        self._completed: deque[TransferItem] = deque(maxlen=max(1, history_limit))
        self._on_queue = on_queue
        self._on_progress = on_progress
        self._on_start = on_start
        self._on_done = on_done
        self._cancel = Event()
        self._stop_after_current = Event()
        self._lock = Lock()
        self._start_lock = Lock()
        self._thread: Thread | None = None
        self._done = Event()
        self._accepting = False

    @staticmethod
    def _normalize(items: list[TransferItem]) -> list[TransferItem]:
        allowed = {"mkdir_remote", "mkdir_local", "upload", "download"}
        if items and all(item.op in allowed for item in items):
            mkdirs = [item for item in items if item.op in {"mkdir_remote", "mkdir_local"}]
            transfers = [item for item in items if item.op in {"upload", "download"}]
            return mkdirs + transfers if mkdirs and transfers else items
        return items
    @property
    def running(self) -> bool:
        return self._thread is not None and not self._done.is_set()

    @property
    def stop_requested(self) -> bool:
        return self._stop_after_current.is_set()

    @property
    def cancel_requested(self) -> bool:
        return self._cancel.is_set()

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
        with self._start_lock:
            previous = self._thread
            if previous and previous.is_alive():
                if not self._done.is_set():
                    return
                previous.join()
            with self._lock:
                if self._done.is_set():
                    self._cancel.clear()
                    self._stop_after_current.clear()
                self._done.clear()
                self._accepting = True
                self._thread = Thread(target=self._run, daemon=True)
                if self._on_start:
                    self._on_start()
                self._thread.start()

    def enqueue(self, items: Iterable[TransferItem]) -> bool:
        """Append work to a currently running queue."""
        additions = list(items)
        if not additions:
            return True
        with self._lock:
            if self._cancel.is_set() or self._stop_after_current.is_set():
                return False
            if not self._accepting or self._done.is_set():
                return False
            self.items.extend(additions)
            self._pending.extend(additions)
        for item in additions:
            self._emit_queue("queued", item)
        return True

    def wait(self, timeout: float | None = None) -> bool:
        return self._done.wait(timeout)

    def cancel_all(self) -> None:
        with self._lock:
            self._cancel.set()
            self._stop_after_current.set()

    def stop_after_current(self) -> None:
        with self._lock:
            self._stop_after_current.set()

    def retry_failed(self) -> int:
        return self.retry_failed_items(None)

    def retry_failed_items(self, items: Iterable[TransferItem] | None) -> int:
        selected = None if items is None else {id(item) for item in items}
        with self._lock:
            if self._thread is not None and not self._done.is_set():
                return 0
            restored = [item for item, _error in self._failed
                        if selected is None or id(item) in selected]
            if not restored:
                return 0
            restored_ids = {id(item) for item in restored}
            self._failed = [(item, error) for item, error in self._failed
                            if id(item) not in restored_ids]
            self._pending = restored + self._pending
            self.items = list(self._pending)
            self._cancel.clear()
            self._stop_after_current.clear()
        # HPC-W06-XFER-010: a retry is a new clear operation state.  Re-announce
        # restored items as queued (mirroring enqueue) so subscribers clear
        # their failed/completed rows instead of showing the item twice.
        for item in restored:
            self._emit_queue("queued", item)
        return len(restored)

    def clear_pending(self) -> None:
        with self._lock:
            self._stop_after_current.set()
            removed = list(self._pending)
            self._pending.clear()
        for item in removed:
            self._emit_queue("removed", item)

    def remove_pending_items(self, items: Iterable[TransferItem]) -> int:
        selected = {id(item) for item in items}
        with self._lock:
            removed = [item for item in self._pending if id(item) in selected]
            self._pending = [item for item in self._pending if id(item) not in selected]
        for item in removed:
            self._emit_queue("removed", item)
        return len(removed)

    def set_pending_priorities(self, items: Iterable[TransferItem], priority: str) -> int:
        """Stable ordering inside transfer runs; never cross a filesystem barrier."""
        if priority not in TRANSFER_PRIORITIES:
            return 0
        selected = {id(item) for item in items}
        ranks = {name: index for index, name in enumerate(TRANSFER_PRIORITIES)}
        with self._lock:
            changed = [item for item in self._pending if id(item) in selected
                       and item.op in {"upload", "download"}]
            for item in changed:
                item.priority = priority
            if changed:
                start = 0
                while start < len(self._pending):
                    if self._pending[start].op not in {"upload", "download"}:
                        start += 1
                        continue
                    end = start + 1
                    while end < len(self._pending) and self._pending[end].op in {"upload", "download"}:
                        end += 1
                    self._pending[start:end] = sorted(
                        self._pending[start:end], key=lambda item: ranks.get(item.priority, 2),
                    )
                    start = end
        for item in changed:
            self._emit_queue("priority", item)
        return len(changed)

    def remove_failed_items(self, items: Iterable[TransferItem] | None = None) -> int:
        selected = None if items is None else {id(item) for item in items}
        with self._lock:
            removed = [item for item, _ in self._failed
                       if selected is None or id(item) in selected]
            removed_ids = {id(item) for item in removed}
            self._failed = [(item, error) for item, error in self._failed
                            if id(item) not in removed_ids]
        for item in removed:
            self._emit_queue("forgotten_failed", item)
        return len(removed)

    def remove_completed_items(self, items: Iterable[TransferItem] | None = None) -> int:
        selected = None if items is None else {id(item) for item in items}
        with self._lock:
            removed = [item for item in self._completed
                       if selected is None or id(item) in selected]
            removed_ids = {id(item) for item in removed}
            self._completed = deque(
                (item for item in self._completed if id(item) not in removed_ids),
                maxlen=self._completed.maxlen,
            )
        for item in removed:
            self._emit_queue("forgotten_completed", item)
        return len(removed)

    def _take_batch(self, previous_op: str | None) -> list[TransferItem]:
        """Claim pending items atomically; stop/clear/remove cannot race selection."""
        with self._lock:
            if self._cancel.is_set() or self._stop_after_current.is_set() or not self._pending:
                self._accepting = False
                return []
            first = self._pending[0]
            limit = self.parallel_limit
            if first.op not in {"upload", "download"} or previous_op in {"delete", "delete_local"}:
                limit = 1
            count = 1
            while (count < min(limit, len(self._pending))
                   and self._pending[count].op in {"upload", "download"}):
                count += 1
            batch = self._pending[:count]
            del self._pending[:count]
            return batch

    @staticmethod
    def _directory_key(item: TransferItem) -> tuple[str, str] | None:
        if item.op in {"upload", "mkdir_remote"}:
            return "remote", posixpath.normpath(item.dst)
        if item.op in {"download", "mkdir_local"}:
            return "local", os.path.normcase(os.path.abspath(item.dst))
        return None

    def _failed_parent(self, item: TransferItem) -> str | None:
        key = self._directory_key(item)
        if key is None:
            return None
        namespace, target = key
        path_module = posixpath if namespace == "remote" else os.path
        with self._lock:
            failed = sorted(self._failed_directories)
        for kind, directory in failed:
            if kind != namespace:
                continue
            # Retrying the mkdir itself must be allowed to clear its failure.
            if directory == target and item.op in {"mkdir_remote", "mkdir_local"}:
                continue
            try:
                if path_module.commonpath((directory, target)) == directory:
                    return directory
            except ValueError:
                # Different drives or mixed absolute/relative remote paths.
                continue
        return None

    def _finish_item(self, item: TransferItem, error: str | None) -> None:
        if item.op in {"mkdir_remote", "mkdir_local"}:
            key = self._directory_key(item)
            with self._lock:
                if error is None:
                    self._failed_directories.discard(key)
                else:
                    self._failed_directories.add(key)
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
            blocked = self._failed_parent(item)
            if blocked is not None:
                raise RuntimeError(f"Destination directory prerequisite failed: {blocked}")

            def progress(done: int, total: int) -> None:
                if self._cancel.is_set():
                    raise TransferCancelled()
                if self._on_progress:
                    self._on_progress(item, int(done), int(total))
            self._run_item(item, progress)
            if self._cancel.is_set():
                return item, "cancelled"
            return item, None
        except TransferCancelled:
            return item, "cancelled"
        except Exception as exc:
            return item, str(exc) or type(exc).__name__

    def _run(self) -> None:
        previous_op = None
        try:
            with ThreadPoolExecutor(max_workers=self.parallel_limit) as executor:
                while batch := self._take_batch(previous_op):
                    for item in batch:
                        self._emit_queue("started", item)
                    previous_op = batch[-1].op
                    if batch[0].op not in {"upload", "download"}:
                        result, error = self._one(batch[0])
                        self._finish_item(result, error)
                        if error == "cancelled":
                            self.cancel_all()
                        continue
                    futures = {executor.submit(self._one, item): item for item in batch}
                    while futures:
                        done, _ = wait(futures, return_when=FIRST_COMPLETED)
                        for future in done:
                            futures.pop(future)
                            result, error = future.result()
                            self._finish_item(result, error)
                            if error == "cancelled":
                                self.cancel_all()
                    # Drain all claimed items before honoring stop/cancel.
        finally:
            with self._lock:
                self._accepting = False
            self._done.set()
            if self._on_done:
                self._on_done()
