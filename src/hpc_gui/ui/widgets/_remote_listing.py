"""Remote listing/cache leaf for the file-manager remote panel.

Owns the off-thread directory-listing channel: ``_DirectoryListingSignals``,
``_DirectoryListingWorker`` (``QRunnable`` on the global ``QThreadPool`` with
``threading.Event`` cancellation, batched delivery), the listing token /
generation protocol, the TTL directory cache, the synchronous ``refresh()``
(the async twin is ``refresh_async``), and the comparison snapshot
commit. Mixed into ``RemoteDirPanel`` as ``RemoteListingMixin``.

Imports Qt core, ``shiboken6``, and lower-level services/config only — never
the local panel, FTP widget, controllers, dialogs, or another branch's
private implementation. Render entry points (``_begin_render``,
``_append_entries``, ``_finish_render``) and error surfacing
(``_show_op_error``) stay owned elsewhere and are reached via ``self``.
"""

from __future__ import annotations

import threading
from time import monotonic
from typing import Dict, Iterable, List, Optional, Tuple

from shiboken6 import isValid

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from hpc_gui.config.storage import get_remote_directory_cache_enabled
from hpc_gui.core.i18n import t
from hpc_gui.services.directory_comparison import ComparableEntry
from hpc_gui.services.files_base import RemoteEntry


# Short enough that a directory a running job writes into does not stay stale
# on screen; long enough that back/up navigation is still instant.
DIRECTORY_CACHE_TTL_SECONDS = 60.0

# Flush a partial listing to the tree at whichever limit trips first, so a
# slow directory paints early without one repaint per entry.
LISTING_BATCH_SIZE = 200
LISTING_BATCH_INTERVAL_SECONDS = 0.05


class _DirectoryListingSignals(QObject):
    batch = Signal(object, object)
    finished = Signal(object)
    failed = Signal(object, object)
    # Always emitted once the run ends, cancelled or not, so the panel knows
    # the shared listing channel is free and a coalesced request may start.
    settled = Signal(object)


class _DirectoryListingWorker(QRunnable):
    """Stream one remote directory listing off the GUI thread.

    Cancelling abandons the backend iterator, which releases the shared
    listing channel, so a fast A->B->C navigation does not keep paying for
    A's traffic.
    """

    def __init__(self, token: object, files, remote_dir: str) -> None:
        super().__init__()
        self.token = token
        self.signals = _DirectoryListingSignals()
        self._files = files
        self._remote_dir = remote_dir
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        self._cancelled.set()

    @Slot()
    def run(self) -> None:
        try:
            self._run()
        finally:
            self.signals.settled.emit(self.token)

    def _run(self) -> None:
        batch: List[RemoteEntry] = []
        try:
            deadline = monotonic() + LISTING_BATCH_INTERVAL_SECONDS
            for entry in self._files.iterdir_entries(self._remote_dir):
                if self._cancelled.is_set():
                    return
                batch.append(entry)
                if len(batch) >= LISTING_BATCH_SIZE or monotonic() >= deadline:
                    self.signals.batch.emit(self.token, batch)
                    batch = []
                    deadline = monotonic() + LISTING_BATCH_INTERVAL_SECONDS
        except Exception as exc:
            if not self._cancelled.is_set():
                self.signals.failed.emit(self.token, exc)
            return
        if self._cancelled.is_set():
            return
        if batch:
            self.signals.batch.emit(self.token, batch)
        self.signals.finished.emit(self.token)


class RemoteListingMixin:
    """Listing concurrency + cache ownership (mixed into ``RemoteDirPanel``)."""

    session: object
    current_dir: str
    views: dict
    _category_dir: str
    _directory_cache: Dict[str, Tuple[float, List[RemoteEntry]]]
    _listing_generation: int
    _listing_worker: Optional[_DirectoryListingWorker]
    _pending_listing: Optional[Tuple[object, str]]
    _streaming_key: str
    _streaming_entries: List[RemoteEntry]
    _snapshot_dir: str
    _snapshot_entries: List[ComparableEntry]

    def _refresh_from_ui(self, *, force: bool = False) -> None:
        files = (self.session or {}).get("files")
        if bool(getattr(files, "supports_progressive_listing", False)):
            self.refresh_async(force=force)  # type: ignore[attr-defined]
        else:
            self.refresh(force=force)  # type: ignore[attr-defined]

    def refresh(self, force: bool = False):
        if not self.session or not self.session.get("files"):
            for v in self.views.values():
                v.clear()
            self._update_navigation_controls()
            return

        category_dir = self._category_dir or self.current_dir
        override = getattr(self, "_listing_override", None)
        if override is not None and override[0] == category_dir:
            entries = list(override[1])
            self._listing_override = None
        else:
            try:
                entries = self._listdir_entries_cached(category_dir, force=bool(force))
            except Exception as e:
                self._show_op_error(
                    f"{t('dirs.load_failed')}: {e}"
                )
                for v in self.views.values():
                    v.clear()
                return

        self._begin_render(category_dir)
        self._append_entries(entries)
        self._finish_render()
        self._record_navigation_visit(category_dir)
        self._commit_snapshot(category_dir, entries)
        self.directoryLoaded.emit(self.current_dir)

    def _cancel_listing_worker(self) -> None:
        """Abandon the in-flight listing but keep the reference until it settles.

        The worker still owns the shared listing channel until its run ends, so
        dropping the reference here would let the next request start a second
        listing that only blocks on the channel lock.
        """
        worker = self._listing_worker
        if worker is not None:
            worker.cancel()

    def _listing_token_is_current(self, token: object) -> bool:
        return isValid(self) and token == ("directory", self._listing_generation)

    def refresh_async(self, force: bool = False) -> bool:
        """Stream a directory into the tree; stale navigations are cancelled."""
        if not self.session or not self.session.get("files"):
            return False
        self._cancel_listing_worker()
        self._pending_listing = None
        self._listing_generation += 1
        token = ("directory", self._listing_generation)
        category_dir = self._category_dir or self.current_dir
        key = self._cache_key(category_dir)
        if not force and get_remote_directory_cache_enabled():
            cached = self._directory_cache.get(key)
            if cached is not None and monotonic() - cached[0] <= DIRECTORY_CACHE_TTL_SECONDS:
                self._listing_override = (category_dir, list(cached[1]))  # type: ignore[attr-defined]
                self.refresh()  # type: ignore[attr-defined]
                return True
        # Clear up front: leaving the previous directory's rows under the new
        # path invites a click on a row that is no longer there.
        self._begin_render(category_dir)  # type: ignore[attr-defined]
        if self._listing_worker is not None:
            # Only the newest request survives: an A->B->C burst never pays for
            # B's traffic, it is replaced before it ever starts.
            self._pending_listing = (token, key)
            return True
        self._start_listing_worker(token, key)
        return True

    def _start_listing_worker(self, token: object, key: str) -> None:
        self._streaming_key = key
        self._streaming_entries = []
        worker = _DirectoryListingWorker(token, self.session["files"], key)
        self._listing_worker = worker
        worker.signals.batch.connect(self._on_listing_batch)
        worker.signals.finished.connect(self._on_listing_finished)
        worker.signals.failed.connect(self._on_listing_failed)
        worker.signals.settled.connect(self._on_listing_settled)
        QThreadPool.globalInstance().start(worker)

    def _on_listing_settled(self, token: object) -> None:
        if not isValid(self):
            return
        worker = self._listing_worker
        if worker is None or worker.token != token:
            return
        self._listing_worker = None
        pending, self._pending_listing = self._pending_listing, None
        if pending is not None and self._listing_token_is_current(pending[0]):
            self._start_listing_worker(*pending)

    def _on_listing_batch(self, token: object, entries: object) -> None:
        if not self._listing_token_is_current(token):
            return
        self._streaming_entries.extend(entries)
        self._append_entries(entries)  # type: ignore[attr-defined]

    def _on_listing_finished(self, token: object) -> None:
        if not self._listing_token_is_current(token):
            return
        self._directory_cache[self._streaming_key] = (
            monotonic(),
            list(self._streaming_entries),
        )
        self._finish_render()  # type: ignore[attr-defined]
        self._record_navigation_visit(self._streaming_key)  # type: ignore[attr-defined]
        self._commit_snapshot(self._streaming_key, self._streaming_entries)
        if self._cache_key(self.current_dir) == self._streaming_key:
            self.directoryLoaded.emit(self.current_dir)  # type: ignore[attr-defined]

    # ---- comparison snapshot --------------------------------------------
    @staticmethod
    def _comparable_entry(entry: RemoteEntry) -> ComparableEntry:
        return ComparableEntry(
            name=entry.name,
            is_dir=bool(entry.is_dir),
            size=int(entry.size or 0),
            mtime=int(entry.mtime or 0),
        )

    def _commit_snapshot(
        self, remote_dir: str, entries: Iterable[RemoteEntry]
    ) -> None:
        """Commit the final listing of a finished generation as the
        comparison source; pending/abandoned streams never reach here."""
        self._snapshot_dir = self._cache_key(remote_dir)
        self._snapshot_entries = [
            self._comparable_entry(entry) for entry in entries
        ]

    def current_entries_snapshot(self) -> tuple[str, List[ComparableEntry]]:
        """Return (path, entries) only when committed for current_dir."""
        key = self._cache_key(self.current_dir or "/")
        if self._snapshot_dir != key:
            return "", []
        return self._snapshot_dir, list(self._snapshot_entries)

    def _on_listing_failed(self, token: object, error: object) -> None:
        if not self._listing_token_is_current(token):
            return
        self._show_op_error(
            f"{t('dirs.load_failed')}: {error}"
        )
        self._finish_render()

    @staticmethod
    def _cache_key(remote_dir: str) -> str:
        return (remote_dir or "/").rstrip("/") or "/"

    @classmethod
    def _normalize_remote_dir(cls, remote_dir: Optional[str]) -> str:
        return cls._cache_key(remote_dir or "/")

    @classmethod
    def _parent_remote_dir(cls, remote_path: str) -> str:
        clean = (remote_path or "/").rstrip("/") or "/"
        if clean == "/":
            return "/"
        return cls._normalize_remote_dir("/".join(clean.split("/")[:-1]) or "/")

    def _invalidate_directory_cache(self, remote_dir: Optional[str] = None) -> None:
        if remote_dir is None:
            self._directory_cache.clear()
            return
        self._directory_cache.pop(self._cache_key(remote_dir), None)

    def _listdir_entries_cached(
        self,
        remote_dir: str,
        *,
        force: bool = False,
    ) -> List[RemoteEntry]:
        if not self.session or not self.session.get("files"):
            return []
        key = self._cache_key(remote_dir)
        if not get_remote_directory_cache_enabled():
            return list(self.session["files"].listdir_entries(key))
        now = monotonic()
        cached = self._directory_cache.get(key)
        if not force and cached is not None:
            cached_at, entries = cached
            if now - cached_at <= DIRECTORY_CACHE_TTL_SECONDS:
                return list(entries)
        entries = list(self.session["files"].listdir_entries(key))
        self._directory_cache[key] = (now, entries)
        return list(entries)


__all__ = [
    "DIRECTORY_CACHE_TTL_SECONDS",
    "LISTING_BATCH_SIZE",
    "LISTING_BATCH_INTERVAL_SECONDS",
    "RemoteListingMixin",
    "_DirectoryListingSignals",
    "_DirectoryListingWorker",
]
