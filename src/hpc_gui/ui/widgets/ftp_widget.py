from __future__ import annotations

from hpc_gui.ui.widgets._legacy_patch_targets import enable_legacy_patch_targets as _enable_legacy_patch_targets

from time import monotonic as monotonic  # noqa: F401 — legacy patch target

from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QApplication as QApplication,  # noqa: F401 — legacy patch target
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from hpc_gui.config.storage import (
    get_ftp_state,
    get_ftp_transfer_type as get_ftp_transfer_type,  # noqa: F401 — test patch compatibility; runtime owner is _ftp_session
    set_transfer_completion_action as set_transfer_completion_action,  # noqa: F401 — legacy patch target
    update_ftp_state,
)
from hpc_gui.services.synchronized_browsing import SyncRoots
from hpc_gui.core.i18n import t, tr as _tr
from hpc_gui.services.transfer_mode import (
    ASCII,
    AUTO,
    BINARY,
)
from hpc_gui.ui.widgets._ftp_activity_menus import (
    ActivityMenusMixin,
    _exec_temporary_menu as _exec_temporary_menu,  # noqa: F401 — legacy re-export
)
from hpc_gui.ui.widgets._ftp_activity_sync import ActivitySyncMixin
from hpc_gui.ui.widgets._ftp_activity_table import ActivityTableMixin
from hpc_gui.ui.widgets._ftp_comparison import FtpComparisonMixin
from hpc_gui.ui.widgets._ftp_session import FtpSessionMixin
from hpc_gui.ui.widgets._ftp_sync_browsing import FtpSyncMixin
from hpc_gui.ui.widgets._ftp_transfer_actions import FtpTransferActionsMixin
from hpc_gui.ui.widgets.local_dir_panel import LocalDirPanel
from hpc_gui.ui.widgets.remote_accordion import RemoteAccordion
from hpc_gui.ui.widgets.remote_dir_panel import RemoteDirPanel

if TYPE_CHECKING:
    from PySide6.QtWidgets import QTreeWidgetItem


class TransferActivityPanel(ActivityTableMixin, ActivitySyncMixin, ActivityMenusMixin, QGroupBox):
    _MAX_VISIBLE_TRANSFER_ROWS = 500

    _COLUMNS = [
        "Server/Local file",
        "Direction",
        "Remote file",
        "Size",
        "Progress",
        "Priority",
        "Status",
    ]
    _PROGRESS_COLUMN = 4

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._active_context_menu: QMenu | None = None
        self._controller = None
        self._controllers: list = []
        self._controller_connections_by_id: dict[int, list[tuple[object, object]]] = {}
        self._finished_errors: list[tuple[object, str]] = []
        self._finished_completed: list = []
        self._last_status_text = _tr("transfer.no_active_transfer", "No active transfer.")
        self._tab_counts = {"queue": 0, "failed": 0, "completed": 0}
        self._progress_by_item: dict[int, int] = {}
        self._row_by_item_id: dict[int, QTreeWidgetItem] = {}
        self._progress_bar_by_item_id: dict[int, QProgressBar] = {}
        self.status_label = QLabel(_tr("transfer.no_active_transfer", "No active transfer."))
        self.summary_label = QLabel()
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.South)
        self.queue_list = self._make_transfer_table()
        self.failed_list = self._make_transfer_table()
        self.completed_list = self._make_transfer_table()
        for view in (
            self.queue_list,
            self.failed_list,
            self.completed_list,
        ):
            view.setMinimumHeight(92)
        self.tabs.addTab(self.queue_list, _tr("transfer.queue_tab", "Queue"))
        self.tabs.addTab(self.failed_list, _tr("transfer.failed_tab", "Failed"))
        self.tabs.addTab(self.completed_list, _tr("transfer.completed_tab", "Completed"))
        for view, kind in (
            (self.queue_list, "queue"),
            (self.failed_list, "failed"),
            (self.completed_list, "completed"),
        ):
            view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            view.customContextMenuRequested.connect(
                lambda pos, current=view, current_kind=kind: self._show_transfer_menu(
                    current,
                    pos,
                    current_kind,
                )
            )

        self.btn_stop = QPushButton(_tr("transfer.stop", "Stop"))
        self.btn_cancel = QPushButton(_tr("transfer.cancel", "Cancel"))
        self.btn_clear_pending = QPushButton(_tr("transfer.clear_pending", "Clear queued"))
        self.btn_stop.clicked.connect(lambda: self._call_controller("cancel_all"))
        self.btn_cancel.clicked.connect(lambda: self._call_controller("cancel_all"))
        self.btn_clear_pending.clicked.connect(lambda: self._call_controller("clear_pending"))
        buttons = QHBoxLayout()
        buttons.addWidget(self.btn_stop)
        buttons.addWidget(self.btn_cancel)
        buttons.addWidget(self.btn_clear_pending)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.tabs)
        layout.addLayout(buttons)
        self._set_controls_enabled(False)
        self._update_summary([])
        self.retranslate_ui()

class FtpWidget(
    FtpSessionMixin,
    FtpSyncMixin,
    FtpComparisonMixin,
    FtpTransferActionsMixin,
    QWidget,
):
    _ACTIVATION_DEBOUNCE_SECONDS = 1.0

    defaultPathsRequested = Signal(str, str)
    openFileRequested = Signal(str)
    submitRequested = Signal(str)
    batchSubmitRequested = Signal(list)
    batchShellRequested = Signal(list)
    runShellRequested = Signal(str)
    editLocalRequested = Signal(str, bool)  # path, new_window

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._active_context_menu: QMenu | None = None
        self.session = None
        self._scratch_path = ""
        self._home_path = ""
        self._recent_activation_transfers: dict[tuple[str, str, str], float] = {}
        state = get_ftp_state()

        self.local_panel = LocalDirPanel(state["local_dir"])
        self.panel_scratch = RemoteDirPanel()
        self.panel_home = RemoteDirPanel()
        self.remote_panels: dict[str, RemoteDirPanel] = {
            "scratch": self.panel_scratch,
            "home": self.panel_home,
        }
        self.panel_scratch.set_transfer_mode_provider(self.current_transfer_mode)
        self.panel_home.set_transfer_mode_provider(self.current_transfer_mode)
        self.panel_scratch.set_local_target_refresh_callback(
            self._refresh_local_transfer_target
        )
        self.panel_home.set_local_target_refresh_callback(
            self._refresh_local_transfer_target
        )
        self.panel_scratch.set_transfer_dialog_visible(False)
        self.panel_home.set_transfer_dialog_visible(False)
        self.transfer_activity = TransferActivityPanel()
        self.panel_scratch.set_transfer_activity_callback(
            self.transfer_activity.record
        )
        self.panel_home.set_transfer_activity_callback(self.transfer_activity.record)
        self.panel_scratch.open_file.connect(self.openFileRequested)
        self.panel_home.open_file.connect(self.openFileRequested)
        self.panel_scratch.file_activated.connect(self._download_remote_path)
        self.panel_home.file_activated.connect(self._download_remote_path)
        self.panel_scratch.download_requested.connect(
            lambda paths, panel=self.panel_scratch: self._download_remote_paths(panel, paths)
        )
        self.panel_home.download_requested.connect(
            lambda paths, panel=self.panel_home: self._download_remote_paths(panel, paths)
        )
        self.panel_scratch.save_as_requested.connect(
            lambda paths, panel=self.panel_scratch: self._save_remote_paths_as(panel, paths)
        )
        self.panel_home.save_as_requested.connect(
            lambda paths, panel=self.panel_home: self._save_remote_paths_as(panel, paths)
        )
        self.panel_scratch.submit_requested.connect(self.submitRequested)
        self.panel_home.submit_requested.connect(self.submitRequested)
        self.panel_scratch.batch_submit_requested.connect(self.batchSubmitRequested)
        self.panel_home.batch_submit_requested.connect(self.batchSubmitRequested)
        self.panel_scratch.batch_shell_requested.connect(self.batchShellRequested)
        self.panel_home.batch_shell_requested.connect(self.batchShellRequested)
        self.panel_scratch.run_shell_requested.connect(self.runShellRequested)
        self.panel_home.run_shell_requested.connect(self.runShellRequested)
        self.panel_scratch.default_location_label = t("ftp.set_scratch_default")
        self.panel_home.default_location_label = t("ftp.set_home_default")
        self.panel_scratch.set_default_requested.connect(
            lambda: self.set_current_as_default("scratch")
        )
        self.panel_home.set_default_requested.connect(
            lambda: self.set_current_as_default("home")
        )
        for key, panel in (
            ("scratch", self.panel_scratch),
            ("home", self.panel_home),
        ):
            panel.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            panel.customContextMenuRequested.connect(
                lambda pos, selected=key, target=panel: self._show_default_menu(
                    selected, target, pos
                )
            )

        self.accordion = RemoteAccordion(
            [
                ("scratch", t("ftp.scratch"), self.panel_scratch),
                ("home", t("ftp.home"), self.panel_home),
            ]
        )
        self.accordion.set_active(state["active_remote"], emit=False)

        self.splitter = QSplitter()
        self.splitter.addWidget(self.local_panel)
        self.splitter.addWidget(self.accordion)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        QTimer.singleShot(0, lambda: self.splitter.setSizes(state["splitter_sizes"]))

        self.transfer_splitter = QSplitter(Qt.Orientation.Vertical)
        self.transfer_splitter.addWidget(self.splitter)
        self.transfer_splitter.addWidget(self.transfer_activity)
        self.transfer_splitter.setStretchFactor(0, 4)
        self.transfer_splitter.setStretchFactor(1, 1)

        self.mode_label = QLabel(t("ftp.transfer_type"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem(t("ftp.mode_auto"), AUTO)
        self.mode_combo.addItem(t("ftp.mode_binary"), BINARY)
        self.mode_combo.addItem(t("ftp.mode_ascii"), ASCII)
        self.apply_settings()
        self.effective_label = QLabel()

        self._sync_navigation_guard = False
        self._sync_status_reason = ""
        self._sync_roots = SyncRoots()
        self.btn_sync_browsing = QToolButton()
        self.btn_sync_browsing.setText(t("ftp.sync_browsing"))
        self.btn_sync_browsing.setCheckable(True)
        self.btn_sync_browsing.setEnabled(False)
        self.btn_sync_browsing.setPopupMode(
            QToolButton.ToolButtonPopupMode.MenuButtonPopup
        )
        sync_menu = QMenu(self.btn_sync_browsing)
        act_reset_roots = sync_menu.addAction(t("ftp.sync_reset_roots"))
        act_disable_sync = sync_menu.addAction(t("ftp.sync_disable"))
        act_reset_roots.triggered.connect(self._reset_synchronized_roots)
        act_disable_sync.triggered.connect(self.btn_sync_browsing.setChecked)
        self.btn_sync_browsing.setMenu(sync_menu)
        self.btn_sync_browsing.toggled.connect(self._on_sync_browsing_toggled)

        self._comparison_waiting_reason = ""
        self.btn_compare_directories = QToolButton()
        self.btn_compare_directories.setText(t("ftp.compare_directories"))
        self.btn_compare_directories.setCheckable(True)
        self.btn_compare_directories.setEnabled(False)
        self.btn_compare_directories.setToolTip(
            t("ftp.compare_directories_tooltip")
        )
        self.btn_compare_directories.toggled.connect(
            self._on_compare_directories_toggled
        )
        self._comparison_recompute_timer = QTimer(self)
        self._comparison_recompute_timer.setSingleShot(True)
        self._comparison_recompute_timer.setInterval(150)
        self._comparison_recompute_timer.timeout.connect(
            self._recompute_directory_comparison
        )

        toolbar = QHBoxLayout()
        toolbar.addWidget(self.mode_label)
        toolbar.addWidget(self.mode_combo)
        toolbar.addWidget(self.effective_label)
        toolbar.addWidget(self.btn_sync_browsing)
        toolbar.addWidget(self.btn_compare_directories)
        toolbar.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(toolbar)
        layout.addWidget(self.transfer_splitter)

        self.mode_combo.currentIndexChanged.connect(self._update_effective_label)
        self.local_panel.selectionChanged.connect(self._update_effective_label)
        self.local_panel.fileActivated.connect(self._upload_local_path)
        self.local_panel.uploadRequested.connect(self._upload_local_paths)
        self.local_panel.editRequested.connect(self.editLocalRequested)
        self.local_panel.remotePathsDropped.connect(self._download_dropped_paths)
        self.local_panel.remoteClipboardPasteRequested.connect(
            self._download_remote_clipboard_paths
        )
        self.local_panel.directoryChanged.connect(
            lambda path: update_ftp_state(local_dir=path)
        )
        self.local_panel.directoryChanged.connect(
            self._on_synchronized_local_dir_changed
        )
        self.panel_scratch.directoryChanged.connect(
            lambda path, panel=self.panel_scratch: self._on_synchronized_remote_dir_changed(path, panel)
        )
        self.panel_home.directoryChanged.connect(
            lambda path, panel=self.panel_home: self._on_synchronized_remote_dir_changed(path, panel)
        )
        self.local_panel.directoryLoaded.connect(
            lambda _path: self._schedule_comparison_recompute()
        )
        for panel in (self.panel_scratch, self.panel_home):
            panel.directoryLoaded.connect(
                lambda _path: self._schedule_comparison_recompute()
            )
        self.accordion.activeChanged.connect(
            lambda _key: self._schedule_comparison_recompute()
        )
        self.accordion.activeChanged.connect(
            lambda key: update_ftp_state(active_remote=key)
        )
        self.splitter.splitterMoved.connect(
            lambda _position, _index: update_ftp_state(
                splitter_sizes=self.splitter.sizes()
            )
        )
        self._update_effective_label()

    def retranslate_ui(self) -> None:
        self.local_panel.retranslate_ui()
        self.mode_label.setText(t("ftp.transfer_type"))
        for index, key in enumerate(("mode_auto", "mode_binary", "mode_ascii")):
            self.mode_combo.setItemText(index, t(f"ftp.{key}"))
        self.btn_sync_browsing.setText(t("ftp.sync_browsing"))
        if not self._sync_status_reason:
            self._set_sync_status("")
        self.btn_compare_directories.setText(t("ftp.compare_directories"))
        self.transfer_activity.retranslate_ui()
        self._update_remote_titles()
        self.panel_scratch.retranslate_ui()
        self.panel_home.retranslate_ui()
        self.panel_scratch.default_location_label = t("ftp.set_scratch_default")
        self.panel_home.default_location_label = t("ftp.set_home_default")
        self._update_effective_label()

    def shutdown(self) -> None:
        self.panel_scratch.shutdown()
        self.panel_home.shutdown()


_enable_legacy_patch_targets(
    __name__,
    {
        "get_ftp_transfer_type": (("hpc_gui.ui.widgets._ftp_session", "get_ftp_transfer_type"),),
        "set_transfer_completion_action": (
            ("hpc_gui.ui.widgets._ftp_activity_menus", "set_transfer_completion_action"),
        ),
        "QMenu": (
            ("hpc_gui.ui.widgets._ftp_activity_menus", "QMenu"),
            ("hpc_gui.ui.widgets._ftp_session", "QMenu"),
        ),
        "monotonic": (("hpc_gui.ui.widgets._ftp_transfer_actions", "monotonic"),),
    },
)
