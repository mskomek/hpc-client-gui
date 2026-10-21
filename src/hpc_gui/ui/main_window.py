"""Qt main window facade (Wave M01).

Composition root for the main window: tab/workspace assembly, timers and
signal wiring live here, with graceful shutdown and close handling.
Menubar/language, plugin-menu, update/changelog and workspace/session
behaviors live in the ``_main_window_*`` mixins composed below.

The re-exported storage/changelog/error helpers are the patch surface
relied on by tests (``hpc_gui.ui.main_window.<name>``); the mixins resolve
them through this module at call time.
"""

import logging

from PySide6.QtCore import QEvent, QThread, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSystemTrayIcon, QTabWidget,
)

from hpc_gui.core._legacy_patch_targets import enable_legacy_patch_targets
from hpc_gui.ui._main_window_contracts import (
    chronological_changelog as chronological_changelog,
    get_last_seen_changelog_version as get_last_seen_changelog_version,
    get_sbatch_follow_mode as get_sbatch_follow_mode,
    load_changelog_text as load_changelog_text,
    set_last_seen_changelog_version as set_last_seen_changelog_version,
    show_exception as show_exception,
)
from hpc_gui.core.debug_telemetry import DebugTelemetry, is_source_run
from hpc_gui.core.i18n import t
from .async_call import AsyncCall
from .splash_screen import UpdateSplash
from .widgets.login_widget import LoginWidget
from .widgets.jobs_outputs_widget import JobsOutputsWidget
from .widgets.directories_widget import DirectoriesWidget
from .widgets.ftp_widget import FtpWidget
from .widgets.editor_widget import EditorWidget
from .widgets.logs_widget import LogsWidget
from ._main_window_menubar import _MainWindowMenubarMixin
from ._main_window_plugins import _MainWindowPluginsMixin
from ._main_window_updates import _BackgroundCall, _MainWindowUpdatesMixin
from ._main_window_workspace import _MainWindowWorkspaceMixin


from pathlib import Path as Path

import shlex as shlex
import threading as threading
import webbrowser as webbrowser

from PySide6.QtCore import (
    QObject as QObject,
    QSize as QSize,
    QThreadPool as QThreadPool,
    Qt as Qt,
    Signal as Signal,
    Slot as Slot,
)
from PySide6.QtGui import (
    QAction as QAction,
    QColor as QColor,
    QIcon as QIcon,
    QPainter as QPainter,
    QPixmap as QPixmap,
)
from PySide6.QtSvg import QSvgRenderer as QSvgRenderer
from PySide6.QtWidgets import (
    QDialog as QDialog,
    QHBoxLayout as QHBoxLayout,
    QLabel as QLabel,
    QMenu as QMenu,
    QMessageBox as QMessageBox,
    QPushButton as QPushButton,
    QSizePolicy as QSizePolicy,
    QTextEdit as QTextEdit,
    QToolButton as QToolButton,
    QVBoxLayout as QVBoxLayout,
    QWidget as QWidget,
)
from hpc_gui.config.storage import (
    SBATCH_FOLLOW_MODE_NEW_TABS_SPLIT as SBATCH_FOLLOW_MODE_NEW_TABS_SPLIT,
    SBATCH_FOLLOW_MODE_OUTPUTS_TAB as SBATCH_FOLLOW_MODE_OUTPUTS_TAB,
    get_squeue_auto_refresh_enabled as get_squeue_auto_refresh_enabled,
)
from hpc_gui.core.paths import is_frozen_exe as is_frozen_exe
from hpc_gui.core.platform import current_os as current_os
from hpc_gui.core.i18n import set_language as set_language
from hpc_gui.services import app_updater as app_updater
from hpc_gui.services.app_updater import (
    AUTOMATIC_INSTALL_STRATEGIES as AUTOMATIC_INSTALL_STRATEGIES,
    download_and_verify_release as download_and_verify_release,
    get_latest_release as get_latest_release,
    is_newer_version as is_newer_version,
    launch_update_installer as launch_update_installer,
)
from .dialogs.help_dialog import HelpDialog as HelpDialog
from .dialogs.settings_dialog import SettingsDialog as SettingsDialog
from .dialogs.send_logs_dialog import SendLogsDialog as SendLogsDialog
from .dialogs.quick_tour import QuickTourOverlay as QuickTourOverlay

from hpc_gui import __version__ as __version__

__all__ = [
    'AUTOMATIC_INSTALL_STRATEGIES',
    'AsyncCall',
    'DebugTelemetry',
    'DirectoriesWidget',
    'EditorWidget',
    'FtpWidget',
    'HelpDialog',
    'JobsOutputsWidget',
    'LoginWidget',
    'LogsWidget',
    'MainWindow',
    'Path',
    'QAction',
    'QApplication',
    'QColor',
    'QDialog',
    'QEvent',
    'QHBoxLayout',
    'QIcon',
    'QLabel',
    'QMainWindow',
    'QMenu',
    'QMessageBox',
    'QObject',
    'QPainter',
    'QPixmap',
    'QPushButton',
    'QSize',
    'QSizePolicy',
    'QSvgRenderer',
    'QSystemTrayIcon',
    'QTabWidget',
    'QTextEdit',
    'QThread',
    'QThreadPool',
    'QTimer',
    'QToolButton',
    'QVBoxLayout',
    'QWidget',
    'Qt',
    'QuickTourOverlay',
    'SBATCH_FOLLOW_MODE_NEW_TABS_SPLIT',
    'SBATCH_FOLLOW_MODE_OUTPUTS_TAB',
    'SendLogsDialog',
    'SettingsDialog',
    'Signal',
    'Slot',
    'UpdateSplash',
    '_BackgroundCall',
    'app_updater',
    'chronological_changelog',
    'current_os',
    'download_and_verify_release',
    'get_last_seen_changelog_version',
    'get_latest_release',
    'get_sbatch_follow_mode',
    'get_squeue_auto_refresh_enabled',
    'is_frozen_exe',
    'is_newer_version',
    'is_source_run',
    'launch_update_installer',
    'load_changelog_text',
    'logging',
    'set_language',
    'set_last_seen_changelog_version',
    'shlex',
    'show_exception',
    't',
    'threading',
    'webbrowser',
]



class MainWindow(
    _MainWindowMenubarMixin,
    _MainWindowPluginsMixin,
    _MainWindowUpdatesMixin,
    _MainWindowWorkspaceMixin,
    QMainWindow,
):

    _logger = logging.getLogger("hpc_gui.ui.main_window")

    def changeEvent(self, event) -> None:  # type: ignore[override]
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange and hasattr(self, "jobs_outputs"):
            self.jobs_outputs.set_application_minimized(self.isMinimized())

    def __init__(self):
        super().__init__()
        self._shutdown_done = False
        self._update_jobs: set[QThread] = set()
        self._update_workers: dict[QThread, _BackgroundCall] = {}
        self._update_busy_count = 0
        self._update_progress: UpdateSplash | None = None
        self._update_manual = False
        self._update_interactive = False
        self._update_cancelled = False
        self._job_poll_worker: AsyncCall | None = None
        self._job_poll_generation = 0
        self._init_language_menu()
        self.retranslate_ui()

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.login = LoginWidget()
        self.jobs_outputs = JobsOutputsWidget()
        self.directories = DirectoriesWidget()
        self.ftp = FtpWidget()
        self.editor = EditorWidget()
        self._editor_windows: list[QMainWindow] = []
        self.logs = LogsWidget()

        self.tabs.addTab(self.login, t("tabs.login"))
        self.tabs.addTab(self.jobs_outputs, t("tabs.jobs_outputs"))
        self.tabs.addTab(self.directories, t("tabs.directories"))
        self.tabs.addTab(self.ftp, t("tabs.ftp") if t("tabs.ftp") != "[tabs.ftp]" else "FTP")
        self.tabs.addTab(self.editor, t("tabs.editor"))
        self.tabs.addTab(
            self.logs, t("tabs.logs") if t("tabs.logs") != "[tabs.logs]" else "Logs"
        )
        if is_source_run():
            telemetry = QApplication.instance().findChild(DebugTelemetry)
            if telemetry is not None:
                telemetry.observe_tab_widget(self.tabs, "main")
        self.tabs.currentChanged.connect(self._sync_command_polling)
        self.jobs_outputs.polling_visibility_changed.connect(
            self._sync_command_polling
        )
        self.jobs_outputs.request_show_directories.connect(self.show_directories)

        self.login.session_changed.connect(self.on_session_changed)
        self.ftp.defaultPathsRequested.connect(
            self.login.update_active_profile_remote_defaults
        )

        # Job completion monitor
        self.job_timer = QTimer(self)
        self.job_timer.setInterval(15000)
        self.job_timer.timeout.connect(self._poll_jobs)
        self._last_job_ids = set()
        self._job_monitor_initialized = False
        self._job_tray = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self._job_tray = QSystemTrayIcon(self)
            tray_icon = self.windowIcon()
            if tray_icon.isNull():
                tray_icon = QApplication.windowIcon()
            self._job_tray.setIcon(tray_icon)
            self._job_tray.show()
        self._sync_command_polling()

        self.directories.open_in_editor.connect(self.open_in_editor)
        self.directories.open_in_editor_new_window.connect(self.open_in_editor_new_window)
        self.directories.script_submitted.connect(self.on_script_submitted)
        self.ftp.openFileRequested.connect(self.directories.on_open_file)
        self.ftp.editLocalRequested.connect(self.open_local_in_editor)
        self.ftp.submitRequested.connect(self.directories.submit_script)
        self.ftp.batchSubmitRequested.connect(self.directories.submit_scripts_batch)
        self.ftp.batchShellRequested.connect(self.run_shell_batch_in_terminal)
        self.ftp.runShellRequested.connect(self.directories.run_shell_script)
        self.editor.script_submitted.connect(self.on_script_submitted)
        self.editor.run_in_terminal_requested.connect(self.run_shell_in_terminal)
        self._startup_changelog_timer = QTimer(self)
        self._startup_changelog_timer.setSingleShot(True)
        self._startup_changelog_timer.timeout.connect(
            self._show_startup_changelog_if_needed
        )
        self._startup_changelog_timer.start(700)
        self._startup_update_timer = QTimer(self)
        self._startup_update_timer.setSingleShot(True)
        self._startup_update_timer.timeout.connect(
            lambda: self._check_for_updates(manual=False)
        )
        self._startup_update_timer.start(1500)

    def graceful_shutdown(self) -> None:
        """Graceful, idempotent shutdown sequence.

        This is called both from closeEvent and QApplication.aboutToQuit.
        It must never raise.
        """
        if getattr(self, "_shutdown_done", False):
            return
        self._shutdown_done = True
        try:
            # 1) Stop timers / background polling
            try:
                if hasattr(self, "job_timer") and self.job_timer:
                    self.job_timer.stop()
                if hasattr(self, "_startup_changelog_timer"):
                    self._startup_changelog_timer.stop()
                if hasattr(self, "_startup_update_timer"):
                    self._startup_update_timer.stop()
                self._cancel_update_jobs()
                self._job_poll_generation += 1
                self._job_poll_worker = None
                if getattr(self, "_job_tray", None):
                    self._job_tray.hide()
            except Exception:
                pass

            # 2) Stop live file watchers
            try:
                if hasattr(self, "jobs_outputs") and self.jobs_outputs and hasattr(self.jobs_outputs, "shutdown"):
                    self.jobs_outputs.shutdown()
            except Exception:
                pass

            # 3) Cancel in-flight file operations (best-effort)
            try:
                if hasattr(self, "directories") and self.directories and hasattr(self.directories, "shutdown"):
                    self.directories.shutdown()
                if hasattr(self, "ftp") and self.ftp and hasattr(self.ftp, "shutdown"):
                    self.ftp.shutdown()
            except Exception:
                pass

            # 4) External processes (VcXsrv / X11 ssh/plink)
            try:
                if hasattr(self, "login") and self.login and hasattr(self.login, "shutdown_external_processes"):
                    self.login.shutdown_external_processes()
            except Exception:
                pass

            # 5) Final marker for file log
            try:
                import logging

                logging.getLogger("hpc_gui").info("graceful shutdown completed")
            except Exception:
                pass
        except Exception:
            pass

    def closeEvent(self, event):
        """Gracefully stop background helper processes on app exit.

        Controlled by app settings:
        - close_vcxsrv_on_exit
        - close_x11_procs_on_exit
        """
        try:
            self.graceful_shutdown()
        except Exception:
            pass
        super().closeEvent(event)

enable_legacy_patch_targets(
    __name__,
    {
        'chronological_changelog': (("hpc_gui.ui._main_window_contracts", 'chronological_changelog'),),
        'get_last_seen_changelog_version': (("hpc_gui.ui._main_window_contracts", 'get_last_seen_changelog_version'),),
        'get_sbatch_follow_mode': (("hpc_gui.ui._main_window_contracts", 'get_sbatch_follow_mode'),),
        'load_changelog_text': (("hpc_gui.ui._main_window_contracts", 'load_changelog_text'),),
        'set_last_seen_changelog_version': (("hpc_gui.ui._main_window_contracts", 'set_last_seen_changelog_version'),),
        'show_exception': (("hpc_gui.ui._main_window_contracts", 'show_exception'),),
    },
)
