from __future__ import annotations

import inspect
import time  # noqa: F401 - compatibility patch target for transfer tests
from threading import Thread as Thread  # noqa: F401
from typing import Callable, List

from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import QListWidgetItem, QMenu  # noqa: F401
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from hpc_gui.core.i18n import t
from hpc_gui.core.debug_telemetry import is_source_run as is_source_run  # noqa: F401
from hpc_gui.core.logging import get_logger as get_logger  # noqa: F401
from hpc_gui.services.transfer_controller import (
    TransferController as TransferController,
    TransferItem,
)
from hpc_gui.ui.dialogs._transfer_dialog_execution import _TransferDialogExecution
from hpc_gui.ui.dialogs._transfer_dialog_queue import _TransferDialogQueue
from hpc_gui.ui.dialogs._transfer_dialog_support import (
    _tr,
    _WorkerThread,  # noqa: F401 - retained as a module-level compatibility hook
)
from hpc_gui.ui.dialogs._transfer_dialog_views import _TransferDialogViews


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
        self.setWindowTitle(_tr("transfer.preflight_title", "Confirm upload plan"))
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
            QTreeWidgetItem(self.plan_list, [t("transfer.remaining").format(hidden=hidden), "", ""])
        self.plan_list.resizeColumnToContents(0)
        self.plan_list.resizeColumnToContents(1)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
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
        for idx, item in enumerate(self._items, start=1):
            if self._cancel:
                self.finished.emit(item, True, t("dirs.cancelled"))
                return
            self.progress.emit(idx, item)
            try:
                self._run_item(item)
            except Exception as exc:
                self.finished.emit(item, False, str(exc))
                return
        self.finished.emit(None, False, "")


class TransferDialog(_TransferDialogViews, _TransferDialogExecution, _TransferDialogQueue, QDialog):
    _MAX_VISIBLE_LIST_ITEMS = 500
    _MAX_HISTORY = 1000
    _PROGRESS_PUBLISH_INTERVAL_MS = 150

    transferStatsChanged = Signal(str)
    transferListsChanged = Signal(object, object, object)
    transferProgressChanged = Signal(object, object, object)
    # Fires when the queue stops for any reason, including a cancel. Owners
    # that reserved something for the duration of the queue must release it
    # here: the dialog stays open after a cancel, so its `finished` signal
    # may never arrive.
    queueFinished = Signal()

    def __init__(
        self,
        parent=None,
        *,
        title: str,
        items: List[TransferItem],
        run_item: Callable[[TransferItem], None],
        parallel_limit: int = 1,
        max_parallel_limit: int = 10,
        configured_limit: int | None = None,
        backend_context_factory=None,
    ) -> None:
        super().__init__(parent)
        self.setModal(False)
        self.setWindowTitle(title or t("dirs.progress_title"))
        self._run_item = run_item
        # Optional factory producing an isolated, closeable files backend for
        # one worker thread (parallel-safe backends such as FTP). The queue
        # bounds concurrency, so at most ``parallel_limit`` extra connections
        # exist; the dialog closes each one in a finally block.
        self._backend_context_factory = backend_context_factory
        # The per-profile setting is the configured value; the value actually
        # used can be lower (backend capability / server channel limits).
        self._configured_limit = (
            max(1, min(10, int(configured_limit))) if configured_limit is not None else None
        )
        try:
            self._run_item_accepts_progress = len(inspect.signature(run_item).parameters) >= 2
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
        self._item_progress_baselines: dict[
            int, tuple[float, float]
        ] = {}  # item_id -> (done, time)
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
        self.lbl_parallel_hint = QLabel(self._parallel_hint_text())
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
