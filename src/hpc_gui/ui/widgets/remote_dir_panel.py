from __future__ import annotations

from hpc_gui.core._legacy_patch_targets import enable_legacy_patch_targets as _enable_legacy_patch_targets

import logging
import weakref
from time import monotonic as monotonic  # noqa: F401 — legacy patch point; runtime owner is _remote_listing
from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import (
    QThread,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QGroupBox,
    QListWidget,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QInputDialog as QInputDialog,  # noqa: F401 — legacy patch target
    QMenu,
    QMessageBox,
    QPushButton,
    QStyle,
    QTabBar,
    QToolButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from hpc_gui.core.i18n import t, tr as _tr  # noqa: F401 — legacy fallback helper
from hpc_gui.config.storage import (
    get_upload_preflight_confirmation_enabled as get_upload_preflight_confirmation_enabled,  # noqa: F401 — legacy patch target
    set_upload_preflight_confirmation_enabled as set_upload_preflight_confirmation_enabled,  # noqa: F401 — legacy patch target
)
from hpc_gui.services.files_base import RemoteEntry
from hpc_gui.services.directory_comparison import ComparableEntry
from hpc_gui.core.platform import current_os
from hpc_gui.services.shortcut_preferences import active_binding
from hpc_gui.ui.dialogs.transfer_dialog import (
    TransferDialog as TransferDialog,  # noqa: F401 — annotation use + legacy re-export
    TransferItem as TransferItem,  # noqa: F401 — annotation use + legacy re-export
    TransferPreflightDialog as TransferPreflightDialog,  # noqa: F401 — legacy re-export
)
from hpc_gui.ui.widgets._fm_dnd_contract import (
    MIME_REMOTE_PATHS as MIME_REMOTE_PATHS,  # noqa: F401 — legacy re-export
    _DragPayload as _DragPayload,  # noqa: F401 — legacy re-export
    _decode_payload as _decode_payload,  # noqa: F401 — legacy re-export
    _encode_payload as _encode_payload,  # noqa: F401 — legacy re-export
)
from hpc_gui.ui.widgets._remote_context_menu import (
    REMOTE_CONTEXT_MENU_LABELS as REMOTE_CONTEXT_MENU_LABELS,  # noqa: F401 — legacy re-export
    RemoteContextMenuMixin,
)
from hpc_gui.ui.widgets._remote_lint_tools import (
    RemoteLintToolsMixin,
    _RemoteLintSignals as _RemoteLintSignals,  # noqa: F401 — legacy re-export
    _RemoteLintWorker as _RemoteLintWorker,  # noqa: F401 — legacy re-export
)
from hpc_gui.ui.widgets._remote_listing import (
    DIRECTORY_CACHE_TTL_SECONDS as DIRECTORY_CACHE_TTL_SECONDS,  # noqa: F401 — legacy re-export
    LISTING_BATCH_INTERVAL_SECONDS as LISTING_BATCH_INTERVAL_SECONDS,  # noqa: F401 — legacy re-export
    LISTING_BATCH_SIZE as LISTING_BATCH_SIZE,  # noqa: F401 — legacy re-export
    RemoteListingMixin,
    _DirectoryListingSignals as _DirectoryListingSignals,  # noqa: F401 — legacy re-export
    _DirectoryListingWorker as _DirectoryListingWorker,  # noqa: F401 — legacy re-export
)
from hpc_gui.ui.widgets._remote_metadata import RemoteMetadataMixin
from hpc_gui.ui.widgets._remote_mutations import (
    RemoteMutationsMixin,
    _PlannedOp as _PlannedOp,  # noqa: F401 — legacy re-export
    _UndoRecord as _UndoRecord,  # noqa: F401 — legacy re-export
)
from hpc_gui.ui.widgets._remote_navigation import RemoteNavigationMixin
from hpc_gui.ui.widgets._remote_permissions_dialog import (
    _PermissionsDialog as _PermissionsDialog,  # noqa: F401 — legacy re-export
    _parse_chmod_mode as _parse_chmod_mode,  # noqa: F401 — legacy re-export
)
from hpc_gui.ui.widgets._remote_transfer_copy_move import RemoteTransferCopyMoveMixin
from hpc_gui.ui.widgets._remote_transfer_download import RemoteTransferDownloadMixin
from hpc_gui.ui.widgets._remote_transfer_exec import (
    RemoteTransferExecMixin,
    _FileOpWorker as _FileOpWorker,  # noqa: F401 — legacy re-export
)
from hpc_gui.ui.widgets._remote_transfer_plan import (
    RemoteTransferPlanMixin,
    _LocalUploadPlanJob as _LocalUploadPlanJob,  # noqa: F401 — legacy re-export
    _TransferPlanWorker as _TransferPlanWorker,  # noqa: F401 — legacy re-export
)
from hpc_gui.ui.widgets._remote_transfer_progress import RemoteTransferProgressMixin
from hpc_gui.ui.widgets._remote_transfer_ui import RemoteTransferUiMixin
from hpc_gui.ui.widgets._remote_transfer_upload import RemoteTransferUploadMixin
from hpc_gui.ui.widgets._remote_transfer_upload_plan import RemoteTransferUploadPlanMixin
from hpc_gui.ui.widgets._remote_tree_view import (
    RemoteTreeViewMixin,
    _FILE_MODE_ROLE as _FILE_MODE_ROLE,  # noqa: F401 — legacy re-export
    _RemoteTree as _RemoteTree,  # noqa: F401 — legacy re-export
    _SORT_MTIME_ROLE as _SORT_MTIME_ROLE,  # noqa: F401 — legacy re-export
    _SORT_NAME_ROLE as _SORT_NAME_ROLE,  # noqa: F401 — legacy re-export
    _SORT_SIZE_ROLE as _SORT_SIZE_ROLE,  # noqa: F401 — legacy re-export
    _SORT_TYPE_ROLE as _SORT_TYPE_ROLE,  # noqa: F401 — legacy re-export
)

logger = logging.getLogger(__name__)


class RemoteDirPanel(
    RemoteListingMixin,
    RemoteTreeViewMixin,
    RemoteMutationsMixin,
    RemoteContextMenuMixin,
    RemoteTransferPlanMixin,
    RemoteTransferExecMixin,
    RemoteTransferProgressMixin,
    RemoteTransferDownloadMixin,
    RemoteTransferUploadPlanMixin,
    RemoteTransferUploadMixin,
    RemoteTransferCopyMoveMixin,
    RemoteNavigationMixin,
    RemoteLintToolsMixin,
    RemoteTransferUiMixin,
    RemoteMetadataMixin,
    QWidget,
):
    _parse_chmod_mode = staticmethod(_parse_chmod_mode)
    open_file = Signal(str)  # remote path (file double click)
    open_file_in_new_window = Signal(str)
    file_activated = Signal(str)
    download_requested = Signal(list)  # remote paths -> FTP widget's local panel
    save_as_requested = Signal(list)  # remote paths -> user-selected local folder
    open_in_slot = Signal(int, str)  # slot_index(0/1), remote path
    open_in_slot_new_window = Signal(int, str)
    open_in_slot_new_tab = Signal(int, str)
    open_in_existing_follower = Signal(str, int, str)
    open_file_follow_new_window = Signal(str)
    submit_requested = Signal(str)  # remote Slurm script path
    batch_submit_requested = Signal(list)  # remote Slurm script paths (sorted, case-insensitive)
    batch_shell_requested = Signal(list)  # remote shell script paths (sorted, case-insensitive)
    run_shell_requested = Signal(str)  # remote shell script path
    set_default_requested = Signal()
    directoryChanged = Signal(str)
    directoryLoaded = Signal(str)

    # registry to refresh source/target panels on move
    _instances: Dict[str, "RemoteDirPanel"] = {}

    # single-level undo (last operation)
    _last_undo: Optional[_UndoRecord] = None

    # This is deliberately process-local.  "Always use this action" is a
    # convenience for the current run, not a persisted preference: a fresh
    # application launch must ask about the first conflict again.
    _session_conflict_action: Optional[str] = None

    @classmethod
    def clear_all_directory_caches(cls) -> None:
        """Drop cached listings for every currently open remote panel."""
        for panel in list(cls._instances.values()):
            try:
                panel._directory_cache.clear()
            except RuntimeError:
                continue

    def __init__(self, title: str = ""):
        super().__init__()
        self.session = None
        self.enable_output_menu = False  # JobsOutputsWidget can turn this on
        self.default_location_label = ""
        self.current_dir = ""
        self._category_dir = ""
        self.title = title
        self._snapshot_dir = ""
        self._snapshot_entries: List[ComparableEntry] = []
        self._comparison_statuses: Optional[dict] = None
        self._transfer_mode_provider: Optional[Callable[[str], str]] = None
        self._output_target_provider: Optional[
            Callable[[], List[Tuple[str, str]]]
        ] = None
        self._transfer_activity_callback: Optional[
            Callable[[str, List[TransferItem], str], None]
        ] = None
        self._local_target_refresh_callback: Optional[Callable[[str], None]] = None
        self._transfer_dialogs: List[TransferDialog] = []
        self._active_transfer_keys: set[tuple[str, str, str]] = set()
        self._local_upload_plan_jobs: Dict[int, _LocalUploadPlanJob] = {}
        self._next_local_upload_plan_id = 0
        self._planning_jobs: Dict[int, Tuple[QThread, _TransferPlanWorker]] = {}
        self._next_planning_job_id = 0
        self._show_transfer_dialog = True
        self._directory_cache: Dict[str, Tuple[float, List[RemoteEntry]]] = {}
        self._listing_generation = 0
        self._listing_worker: Optional[_DirectoryListingWorker] = None
        self._remote_lint_worker: Optional[_RemoteLintWorker] = None
        self._pending_listing: Optional[Tuple[object, str]] = None
        self._dirty_views: set[str] = set()
        self._navigation_store = None
        self._pending_select_name = ""
        self._streaming_key = ""
        self._streaming_entries: List[RemoteEntry] = []

        self.panel_id = str(id(self))
        RemoteDirPanel._instances[self.panel_id] = self
        panel_ref = weakref.ref(self)
        self.destroyed.connect(
            lambda _object=None, panel_id=self.panel_id, expected_ref=panel_ref: (
                RemoteDirPanel._unregister_instance_ref(
                    panel_id,
                    expected_ref,
                )
            )
        )
        self.setAcceptDrops(True)

        self.lbl = QLabel(title)
        self.path = QLineEdit()
        self.path.returnPressed.connect(self._open_path_field)

        self.btn_upload = QPushButton(t("dirs.upload"))
        self.btn_upload.clicked.connect(self.upload_files)

        self.btn_new_folder = QPushButton(
            t("dirs.new_folder")
        )
        self.btn_new_folder.clicked.connect(self.create_new_folder)

        self.btn_new_file = QPushButton(
            t("dirs.new_file")
        )
        self.btn_new_file.clicked.connect(self.create_new_file)

        self.btn_template_upload = QPushButton(
            t("dirs.template_upload")
        )
        self.btn_template_upload.clicked.connect(self.show_template_upload_menu)

        self.btn_download = QPushButton(
            t("dirs.download_selected")       )
        self.btn_download.clicked.connect(self.download_selected)

        self.btn_delete = QPushButton(t("dirs.delete"))
        self.btn_delete.clicked.connect(self.delete_selected)

        self.btn_undo = QPushButton(t("dirs.undo"))
        self.btn_undo.clicked.connect(self.undo_last)

        self.btn_parent = QToolButton()
        self.btn_parent.setAutoRaise(False)
        self.btn_parent.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.btn_parent.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
        self.btn_parent.clicked.connect(self.go_parent)
        self.btn_parent.setEnabled(False)

        self.btn_favorites = QToolButton()
        self.btn_favorites.setText(
            t("dirs.favorites")       )
        self.btn_favorites.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_favorites.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.btn_favorites.setMenu(QMenu(self.btn_favorites))
        self.btn_favorites.menu().aboutToShow.connect(self._populate_favorites_menu)

        self.btn_history = QToolButton()
        self.btn_history.setText(
            t("dirs.history")       )
        self.btn_history.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_history.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.btn_history.setMenu(QMenu(self.btn_history))
        self.btn_history.menu().aboutToShow.connect(self._populate_history_menu)

        self.btn_refresh = QPushButton(t("dirs.refresh"))
        self.btn_refresh.clicked.connect(lambda: self._refresh_from_ui(force=True))

        self.refresh_shortcut = QShortcut(QKeySequence.Refresh, self)
        self.refresh_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.refresh_shortcut.activated.connect(lambda: self._refresh_from_ui(force=True))

        top = QHBoxLayout()
        top.addWidget(self.lbl)
        top.addStretch(1)
        top.addWidget(self.btn_new_folder)
        top.addWidget(self.btn_new_file)
        top.addWidget(self.btn_upload)
        top.addWidget(self.btn_template_upload)
        top.addWidget(self.btn_download)
        top.addWidget(self.btn_delete)
        top.addWidget(self.btn_undo)
        top.addWidget(self.btn_parent)
        top.addWidget(self.btn_favorites)
        top.addWidget(self.btn_history)
        top.addWidget(self.btn_refresh)

        self.directory_tabs = QTabBar()
        self.directory_tabs.setExpanding(False)
        self.directory_tabs.setMovable(True)
        self.directory_tabs.setTabsClosable(True)
        self.directory_tabs.tabCloseRequested.connect(self._close_directory_tab)
        self.directory_tabs.currentChanged.connect(self._on_directory_tab_changed)

        self.tabs = QTabWidget()
        self.views: Dict[str, _RemoteTree] = {
            "all": self._make_view(),
            "folders": self._make_view(),
            "iso": self._make_view(),
            "archives": self._make_view(),
            "slurm": self._make_view(),
            "shell": self._make_view(),
            "other": self._make_view(),
        }
        self.tabs.addTab(self.views["all"], t("dirs.tab_all"))
        self.tabs.addTab(self.views["folders"], t("dirs.tab_folders"))
        self.tabs.addTab(self.views["iso"], t("dirs.tab_iso"))
        self.tabs.addTab(
            self.views["archives"], t("dirs.tab_archives")        )
        self.tabs.addTab(self.views["slurm"], t("dirs.tab_slurm"))
        self.tabs.addTab(self.views["shell"], t("dirs.tab_shell"))
        self.tabs.addTab(self.views["other"], t("dirs.tab_other"))
        self.tabs.currentChanged.connect(self._on_tab_changed)

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        self.path_label = QLabel(t("dirs.path"))
        lay.addWidget(self.path_label)
        lay.addWidget(self.path)
        lay.addWidget(self.directory_tabs)
        lay.addWidget(self.tabs)

        # Transfer queue (batch view)
        self.queue_group = QGroupBox(t("dirs.queue_title"))
        qlay = QVBoxLayout(self.queue_group)
        self.queue_current = QLabel("-")
        self.queue_list = QListWidget()
        self.queue_list.setMinimumHeight(80)
        self.queue_current_label = QLabel(t("dirs.queue_current"))
        qlay.addWidget(self.queue_current_label)

        # ---- active batch tracking (for graceful shutdown / diagnostics)
        self._active_thread: Optional[QThread] = None
        self._active_worker: Optional[_FileOpWorker] = None
        self._active_plan: List[_PlannedOp] = []
        self._active_step: int = 0
        self._active_title: str = ""
        qlay.addWidget(self.queue_current)
        self.queue_next_label = QLabel(t("dirs.queue_pending"))
        qlay.addWidget(self.queue_next_label)
        qlay.addWidget(self.queue_list)
        self.queue_group.setVisible(False)
        lay.addWidget(self.queue_group)

        self._update_undo_enabled()
        self._update_navigation_controls()

    def retranslate_ui(self) -> None:
        self.btn_new_folder.setText(t("dirs.new_folder"))
        self.btn_new_file.setText(t("dirs.new_file"))
        self.btn_upload.setText(t("dirs.upload"))
        self.btn_template_upload.setText(t("dirs.template_upload"))
        self.btn_download.setText(t("dirs.download_selected"))
        self.btn_delete.setText(t("dirs.delete"))
        self.btn_undo.setText(t("dirs.undo"))
        self.btn_refresh.setText(t("dirs.refresh"))
        binding = active_binding("FILE-NEW-FOLDER", current_os())
        self.btn_new_folder.setToolTip(f"{t('dirs.new_folder')} ({binding})" if binding else t("dirs.new_folder"))
        self.path_label.setText(t("dirs.path"))
        self.queue_group.setTitle(t("dirs.queue_title"))
        self.queue_current_label.setText(t("dirs.queue_current"))
        self.queue_next_label.setText(t("dirs.queue_pending"))
        tab_keys = ("all", "folders", "iso", "archives", "slurm", "shell", "other")
        for index, key in enumerate(tab_keys):
            self.tabs.setTabText(index, t(f"dirs.tab_{key}"))
        for index in range(self.directory_tabs.count()):
            directory = str(self.directory_tabs.tabData(index) or "")
            if directory:
                self.directory_tabs.setTabText(index, self._directory_tab_label(directory))
        headers = [
            t("dirs.col_name"),
            t("dirs.col_size"),
            t("dirs.col_type"),
            t("dirs.col_mtime"),
            t("ftp.comparison_column"),
        ]
        for view in self.views.values():
            view.setHeaderLabels(headers)

    def _unregister_instance(self, *_args) -> None:
        if RemoteDirPanel._instances.get(self.panel_id) is self:
            RemoteDirPanel._instances.pop(self.panel_id, None)

    @staticmethod
    def _unregister_instance_ref(panel_id: str, expected_ref) -> None:
        expected = expected_ref()
        if (
            expected is not None
            and RemoteDirPanel._instances.get(panel_id) is expected
        ):
            RemoteDirPanel._instances.pop(panel_id, None)

    # ---------- friendly errors (permission/quota UX) ----------
    def _humanize_error(self, raw: str) -> Tuple[str, str]:
        """Return (title, short_message), raw goes to details."""
        text = (raw or "").strip()
        lo = text.lower()

        if "permission denied" in lo or "access is denied" in lo:
            return t("errors.permission_denied"), t("errors.permission_denied_detail")

        if "no space left on device" in lo or "disk quota exceeded" in lo or "quota exceeded" in lo:
            return t("errors.no_space"), t("errors.no_space_detail")

        if "read-only file system" in lo:
            return t("errors.read_only"), t("errors.read_only_detail")

        # fallback
        return t("common.error"), t("errors.operation_failed_detail")

    def _show_op_error(self, raw: str) -> None:
        title, short = self._humanize_error(raw)
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle(title)
        box.setText(short)
        box.setDetailedText(raw)
        box.exec()

    # ---------- transfer-plan Qt dispatchers ----------
    # Thin QObject-owned slots so worker signals bind to this panel's real
    # meta-object and Qt delivers them on the GUI thread. The transfer-plan
    # mixin holds the single implementation; these contain no business logic.
    @Slot(int, str, object)
    def _on_transfer_plan_finished(self, job_id: int, kind: str, result) -> None:
        super()._on_transfer_plan_finished(job_id, kind, result)

    @Slot(int, str, object)
    def _on_transfer_plan_failed(self, job_id: int, _kind: str, exc) -> None:
        super()._on_transfer_plan_failed(job_id, _kind, exc)


_enable_legacy_patch_targets(
    __name__,
    {
        "QInputDialog": (
            ("hpc_gui.ui.widgets._remote_mutations", "QInputDialog"),
            ("hpc_gui.ui.widgets._remote_transfer_plan", "QInputDialog"),
        ),
        "QMenu": (
            ("hpc_gui.ui.widgets._remote_context_menu", "QMenu"),
            ("hpc_gui.ui.widgets._remote_transfer_ui", "QMenu"),
        ),
        "QMessageBox": (
            ("hpc_gui.ui.widgets._remote_context_menu", "QMessageBox"),
            ("hpc_gui.ui.widgets._remote_lint_tools", "QMessageBox"),
            ("hpc_gui.ui.widgets._remote_metadata", "QMessageBox"),
            ("hpc_gui.ui.widgets._remote_mutations", "QMessageBox"),
            ("hpc_gui.ui.widgets._remote_permissions_dialog", "QMessageBox"),
            ("hpc_gui.ui.widgets._remote_transfer_plan", "QMessageBox"),
            ("hpc_gui.ui.widgets._remote_transfer_ui", "QMessageBox"),
        ),
        "monotonic": (("hpc_gui.ui.widgets._remote_listing", "monotonic"),),
        "TransferDialog": (("hpc_gui.ui.widgets._remote_transfer_exec", "TransferDialog"),),
        "TransferPreflightDialog": (
            ("hpc_gui.ui.widgets._remote_transfer_plan", "TransferPreflightDialog"),
        ),
        "get_upload_preflight_confirmation_enabled": (
            ("hpc_gui.ui.widgets._remote_transfer_plan", "get_upload_preflight_confirmation_enabled"),
        ),
        "set_upload_preflight_confirmation_enabled": (
            ("hpc_gui.ui.widgets._remote_transfer_plan", "set_upload_preflight_confirmation_enabled"),
        ),
        "_PermissionsDialog": (("hpc_gui.ui.widgets._remote_metadata", "_PermissionsDialog"),),
    },
)
