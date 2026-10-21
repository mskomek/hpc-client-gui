"""Jobs and live output UI facade."""
from __future__ import annotations
import html
import re
import shlex
import time
from PySide6.QtCore import QEvent, QThreadPool, QTimer, Qt, Signal
from PySide6.QtGui import QFontDatabase, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QTabBar,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from shiboken6 import isValid
from hpc_gui.config.storage import (
    SBATCH_FOLLOW_MODE_NEW_TABS_SPLIT,
    SBATCH_FOLLOW_MODE_NEW_WINDOW_COMBINED,
    SBATCH_FOLLOW_MODE_NEW_WINDOWS_SPLIT,
    SBATCH_FOLLOW_MODE_NONE,
    SBATCH_FOLLOW_MODE_OUTPUTS_TAB,
    get_follow_window_open_minimized_enabled,
    get_jobs_outputs_refresh_interval_seconds,
    get_live_tracking_warning_interval_seconds,
    get_lssrv_auto_refresh_enabled,
    get_pause_live_follow_when_minimized_enabled,
    get_sacct_auto_refresh_enabled,
    get_squeue_auto_refresh_enabled,
)
from hpc_gui.core.history import append_event
from hpc_gui.core.i18n import t
from hpc_gui.core.ui_errors import show_exception
from hpc_gui.config.system_profile import format_remote_path, normalize_system_settings
from hpc_gui.ui.widgets.remote_dir_panel import RemoteDirPanel
from hpc_gui.services.slurm_models import is_active_state, parse_scontrol, parse_squeue
from hpc_gui.services.slurm_script_parser import (
    parse_job_name,
    parse_job_paths,
    storage_area_for_path,
)
from hpc_gui.services.job_tracking_controller import JobTrackingController
from hpc_gui.ui.async_call import AsyncCall
from ._jobs_outputs_lifecycle import _JobsOutputsLifecycleMixin
from ._jobs_outputs_jobs import _JobsOutputsJobsMixin
from ._jobs_outputs_followers import _JobsOutputsFollowersMixin
from ._jobs_outputs_live import _JobsOutputsLiveMixin
from ._jobs_output_text import _ANSI_TOKEN_RE, _ANSI_COLORS, _LIVE_TAIL_INTERVAL_MS, _LIVE_TAIL_LINE_COUNT, _LIVE_TAIL_MAX_RETRY_INTERVAL_MS, _LIVE_TAIL_SLOW_INTERVAL_MS, _LIVE_TAIL_FILE_RETRY_INTERVAL_MS, _LIVE_TAIL_INITIAL_RETRY_SECONDS, _LIVE_TAIL_FILE_RETRY_WINDOW_SECONDS, _OUTPUT_MAX_LINES, _OUTPUT_TRUNCATION_MARKER, _ansi_prefix_for_tail, _bounded_output_text, _ansi_to_html
from ._jobs_output_rendering import _apply_terminal_output_style as _render_terminal_output_style
from ._jobs_output_follower_views import _NavigableTextEdit, _OutputFollowerWidget
from ._jobs_output_follower_windows import _FollowerWindow, _SingleFileFollowerWidget

class JobsOutputsWidget(_JobsOutputsLifecycleMixin, _JobsOutputsJobsMixin, _JobsOutputsFollowersMixin, _JobsOutputsLiveMixin, QWidget):
    polling_visibility_changed = Signal()
    request_show_directories = Signal()

    def __init__(self):
        super().__init__()
        self.session = None
        self._tracking = JobTrackingController()
        self._page_active = True

        self.active_script: str = ""
        self.active_out: str = ""
        self.active_err: str = ""
        self._last_sig = [None, None]  # (size,mtime) for out/err
        self._tail_paused = False
        self._paused_for_minimize = False
        self._main_window_minimized = False
        self._async_workers: set[AsyncCall] = set()
        self._async_busy: dict[str, int] = {}
        self._session_generation = 0
        self._live_tail_failures = 0
        self._live_tail_last_content: tuple[str, ...] | None = None
        self._live_tail_last_change = time.monotonic()
        self._tail_suspended = False
        self._tail_alert_visible = False
        self._tail_stop_notified = False
        self._live_tail_failure_started: float | None = None
        self._minimize_started_at: float | None = None
        self._detail_scheduler_paths: tuple[str, str] = ("", "")
        self._follow_windows: list[QMainWindow] = []
        self._single_file_follow_windows: list[QMainWindow] = []
        self._follow_tabs: list[_OutputFollowerWidget] = []
        self._follow_tab_target_ids: dict[_OutputFollowerWidget, str] = {}
        self._follow_targets: dict[str, _OutputFollowerWidget] = {}
        self._follow_target_labels: dict[str, str] = {}
        self._follow_target_order: list[str] = []
        self._next_follow_window_number = 1
        self._next_follow_tab_number = 1
        self.destroyed.connect(self._invalidate_async_callbacks)

        self.section_tabs = QTabWidget(self)
        self.details_tab = QWidget(self.section_tabs)
        self.files_tab = QWidget(self.section_tabs)
        self.outputs_tab = QWidget(self.section_tabs)

        # --- Jobs box
        self.jobs_box = QGroupBox(t("jobs.title"))
        self.jobs_text = QTextEdit()
        self.jobs_text.setReadOnly(True)
        self._apply_terminal_output_style(self.jobs_text)
        self.jobs_text.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.jobs_text.customContextMenuRequested.connect(self._show_jobs_context_menu)

        self.btn_refresh = QPushButton(t("jobs.refresh"))
        self.btn_refresh.clicked.connect(self.refresh_jobs)

        self.cancel_id = QLineEdit()
        self.cancel_id.setPlaceholderText(t("jobs.job_id"))
        self.btn_cancel = QPushButton(t("jobs.cancel"))
        self.btn_cancel.clicked.connect(self.cancel_job)

        row = QHBoxLayout()
        row.addWidget(self.btn_refresh)
        row.addStretch(1)
        row.addWidget(self.cancel_id)
        row.addWidget(self.btn_cancel)

        vj = QVBoxLayout(self.jobs_box)
        vj.addLayout(row)
        vj.addWidget(self.jobs_text)

        # --- Accounting / details box
        self.meta_box = QGroupBox(t("jobs_outputs.accounting_details"))
        self.meta_text = QTextEdit()
        self.meta_text.setReadOnly(True)
        self.meta_text.setPlaceholderText(t("jobs_outputs.accounting_placeholder"))
        self._apply_terminal_output_style(self.meta_text)
        self.meta_job_id = QLineEdit()
        self.meta_job_id.setPlaceholderText(t("jobs.job_id"))
        self.meta_job_script = QLabel()
        self.meta_job_script.setTextFormat(Qt.TextFormat.RichText)
        self.meta_job_script.setOpenExternalLinks(False)
        self.meta_job_script.linkActivated.connect(self._open_detail_script)
        self.meta_job_workdir = QLabel()
        self.btn_sacct = QPushButton(t("jobs_outputs.refresh_sacct"))
        self.btn_scontrol = QPushButton(t("jobs_outputs.show_job_details"))
        self.btn_sacct.clicked.connect(self.refresh_sacct)
        self.btn_scontrol.clicked.connect(self.show_job_details)
        meta_row = QHBoxLayout()
        meta_row.addWidget(self.btn_sacct)
        meta_row.addStretch(1)
        meta_row.addWidget(self.meta_job_id)
        meta_row.addWidget(self.btn_scontrol)
        vm = QVBoxLayout(self.meta_box)
        vm.addLayout(meta_row)
        vm.addWidget(self.meta_job_script)
        vm.addWidget(self.meta_job_workdir)
        vm.addWidget(self.meta_text)

        # --- lssrv
        self.lssrv_box = QGroupBox()
        self.btn_lssrv = QPushButton()
        self.btn_lssrv.clicked.connect(self.refresh_lssrv)
        self.lssrv_text = QTextEdit()
        self.lssrv_text.setReadOnly(True)
        self._apply_terminal_output_style(self.lssrv_text)
        lssrv_layout = QVBoxLayout(self.lssrv_box)
        lssrv_row = QHBoxLayout()
        lssrv_row.addWidget(self.btn_lssrv)
        lssrv_row.addStretch(1)
        lssrv_layout.addLayout(lssrv_row)
        lssrv_layout.addWidget(self.lssrv_text)

        # --- Scratch panel (Files subtab)
        self.scratch_panel = RemoteDirPanel(title=t("jobs_outputs.scratch_title"))
        self.scratch_panel.open_file.connect(self.load_one_file)  # double click
        self.scratch_panel.enable_output_menu = True
        self.scratch_panel.open_in_slot.connect(self.open_in_output_slot)
        self.scratch_panel.open_in_slot_new_window.connect(
            self.open_in_output_window
        )
        self.scratch_panel.open_in_slot_new_tab.connect(self.open_in_output_tab)
        self.scratch_panel.open_file_follow_new_window.connect(
            self.open_file_follow_window
        )
        self.scratch_panel.set_output_target_provider(self._output_target_choices)
        self.scratch_panel.open_in_existing_follower.connect(
            self.open_in_existing_follower
        )
        self.btn_files_refresh = QPushButton()
        self.btn_files_refresh.clicked.connect(self.scratch_panel.refresh)

        details_layout = QVBoxLayout(self.details_tab)
        details_layout.addWidget(self.jobs_box)
        details_layout.addWidget(self.meta_box)
        details_layout.addWidget(self.lssrv_box, 2)

        files_layout = QVBoxLayout(self.files_tab)
        files_refresh_row = QHBoxLayout()
        files_refresh_row.addWidget(self.btn_files_refresh)
        files_refresh_row.addStretch(1)
        files_layout.addLayout(files_refresh_row)
        files_layout.addWidget(self.scratch_panel)

        # --- Outputs group (2 panels)
        self.out_group = QGroupBox(t("jobs_outputs.outputs_title"))
        outputs_layout = QVBoxLayout(self.outputs_tab)
        vg = QVBoxLayout(self.out_group)

        self.lbl_script = QLabel(t("jobs_outputs.no_script"))
        vg.addWidget(self.lbl_script)
        self.btn_tail_pause = QPushButton()
        self.btn_tail_pause.clicked.connect(self._toggle_tail_pause)
        self.btn_tail_pause.setVisible(False)
        tail_controls = QHBoxLayout()
        tail_controls.addWidget(self.btn_tail_pause)
        tail_controls.addStretch(1)
        vg.addLayout(tail_controls)

        # Output-1: stdout
        self.out_box = QGroupBox(t("jobs_outputs.output_stdout"))
        v1 = QVBoxLayout(self.out_box)
        self.path_out = QLineEdit()
        self.path_out.returnPressed.connect(lambda: self._follow_path_from_field(0))
        self.search_out = QLineEdit()
        self.btn_search_out = QPushButton()
        self.search_out.returnPressed.connect(lambda: self._find_in_output(0))
        self.btn_search_out.clicked.connect(lambda: self._find_in_output(0))
        search_out_row = QHBoxLayout()
        search_out_row.addWidget(self.search_out)
        search_out_row.addWidget(self.btn_search_out)
        self.txt_out = _NavigableTextEdit()
        self.txt_out.setReadOnly(True)
        v1.addWidget(self.path_out)
        v1.addLayout(search_out_row)
        v1.addWidget(self.txt_out)

        # Output-2: stderr
        self.err_box = QGroupBox(t("jobs_outputs.output_stderr"))
        v2 = QVBoxLayout(self.err_box)
        self.path_err = QLineEdit()
        self.path_err.returnPressed.connect(lambda: self._follow_path_from_field(1))
        self.search_err = QLineEdit()
        self.btn_search_err = QPushButton()
        self.search_err.returnPressed.connect(lambda: self._find_in_output(1))
        self.btn_search_err.clicked.connect(lambda: self._find_in_output(1))
        search_err_row = QHBoxLayout()
        search_err_row.addWidget(self.search_err)
        search_err_row.addWidget(self.btn_search_err)
        self.txt_err = _NavigableTextEdit()
        self.txt_err.setReadOnly(True)
        v2.addWidget(self.path_err)
        v2.addLayout(search_err_row)
        v2.addWidget(self.txt_err)

        vg.addWidget(self.out_box)
        vg.addWidget(self.err_box)
        outputs_layout.addWidget(self.out_group)
        outputs_layout.addStretch(1)

        # --- Live timer
        self._live_timer = QTimer(self)
        self._apply_live_refresh_interval()
        self._live_timer.timeout.connect(self._poll_live)

        self._jobs_refresh_timer = QTimer(self)
        self._jobs_refresh_timer.timeout.connect(self._poll_jobs_and_lssrv)
        self.apply_refresh_settings()

        # --- main layout
        main = QVBoxLayout(self)
        main.addWidget(self.section_tabs)
        self.section_tabs.addTab(self.details_tab, "")
        self.section_tabs.addTab(self.files_tab, "")
        self.section_tabs.addTab(self.outputs_tab, "")
        self.section_tabs.setTabsClosable(True)
        self.section_tabs.tabCloseRequested.connect(self._close_follow_tab)
        for index in range(3):
            self.section_tabs.tabBar().setTabButton(
                index,
                QTabBar.ButtonPosition.RightSide,
                None,
            )
        self.section_tabs.setCurrentIndex(0)
        self.section_tabs.currentChanged.connect(
            self._on_section_tab_changed
        )
        self.retranslate_ui()
    @staticmethod
    def _apply_terminal_output_style(widget: QTextEdit) -> None:
        _render_terminal_output_style(widget)

    def _show_jobs_context_menu(self, position) -> None:
        cursor = self.jobs_text.cursorForPosition(position)
        line = cursor.block().text().strip()
        fields = line.split(None, 1)
        if not fields:
            return
        job_id = fields[0]
        job = next(
            (
                item
                for item in parse_squeue(self.jobs_text.toPlainText())
                if item.job_id == job_id
            ),
            None,
        )
        if job is None:
            return
        menu = QMenu(self.jobs_text)
        cancel_action = menu.addAction(t("jobs.cancel"))
        has_slurm = bool(self.session and self.session.get("slurm"))
        cancel_action.setEnabled(is_active_state(job.state) and has_slurm)
        cancel_action.triggered.connect(
            lambda: self._cancel_job_from_menu(job.job_id)
        )
        menu.exec(self.jobs_text.mapToGlobal(position))

    def _cancel_job_from_menu(self, job_id: str) -> None:
        confirmation = t("jobs.cancel_confirm").format(job_id=job_id)
        if QMessageBox.question(
            self,
            t("jobs.cancel"),
            confirmation,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        self.cancel_id.setText(job_id)
        self.cancel_job()

__all__ = [
"annotations",
"html",
"re",
"shlex",
"time",
"QEvent",
"QThreadPool",
"QTimer",
"Qt",
"Signal",
"QFontDatabase",
"QTextCursor",
"QCheckBox",
"QGroupBox",
"QHBoxLayout",
"QLabel",
"QLineEdit",
"QMainWindow",
"QMenu",
"QMessageBox",
"QPushButton",
"QTabBar",
"QTabWidget",
"QTextEdit",
"QVBoxLayout",
"QWidget",
"isValid",
"SBATCH_FOLLOW_MODE_NEW_TABS_SPLIT",
"SBATCH_FOLLOW_MODE_NEW_WINDOW_COMBINED",
"SBATCH_FOLLOW_MODE_NEW_WINDOWS_SPLIT",
"SBATCH_FOLLOW_MODE_NONE",
"SBATCH_FOLLOW_MODE_OUTPUTS_TAB",
"get_follow_window_open_minimized_enabled",
"get_jobs_outputs_refresh_interval_seconds",
"get_live_tracking_warning_interval_seconds",
"get_lssrv_auto_refresh_enabled",
"get_pause_live_follow_when_minimized_enabled",
"get_sacct_auto_refresh_enabled",
"get_squeue_auto_refresh_enabled",
"t",
"show_exception",
"append_event",
"RemoteDirPanel",
"is_active_state",
"parse_scontrol",
"parse_squeue",
"JobTrackingController",
"parse_job_name",
"parse_job_paths",
"storage_area_for_path",
"format_remote_path",
"normalize_system_settings",
"AsyncCall",
"JobsOutputsWidget",
"_ANSI_TOKEN_RE",
"_ANSI_COLORS",
"_LIVE_TAIL_INTERVAL_MS",
"_LIVE_TAIL_LINE_COUNT",
"_LIVE_TAIL_MAX_RETRY_INTERVAL_MS",
"_LIVE_TAIL_SLOW_INTERVAL_MS",
"_LIVE_TAIL_FILE_RETRY_INTERVAL_MS",
"_LIVE_TAIL_INITIAL_RETRY_SECONDS",
"_LIVE_TAIL_FILE_RETRY_WINDOW_SECONDS",
"_OUTPUT_MAX_LINES",
"_OUTPUT_TRUNCATION_MARKER",
"_ansi_prefix_for_tail",
"_bounded_output_text",
"_ansi_to_html",
"_NavigableTextEdit",
"_OutputFollowerWidget",
"_SingleFileFollowerWidget",
"_FollowerWindow",
]
