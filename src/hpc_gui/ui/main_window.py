import logging
import shlex
import threading
import webbrowser
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QDialog, QMainWindow, QMessageBox,
    QSystemTrayIcon, QTabWidget, QTextEdit, QVBoxLayout, QPushButton
)
from PySide6.QtWidgets import (
    QMenu, QToolButton, QWidget, QSizePolicy, QHBoxLayout, QLabel
)
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import QObject, QThread, QThreadPool, QTimer, Qt, QSize, Signal, Slot, QEvent
from PySide6.QtSvg import QSvgRenderer

from hpc_gui import __version__
from hpc_gui.config.storage import (
    get_last_seen_changelog_version,
    set_last_seen_changelog_version,
)
from hpc_gui.core.paths import is_frozen_exe
from hpc_gui.core.platform import current_os
from hpc_gui.core.i18n import t, set_language
from hpc_gui.core.debug_telemetry import DebugTelemetry, is_source_run
from hpc_gui.core.ui_errors import show_exception
from hpc_gui.services.changelog import chronological_changelog, load_changelog_text
from hpc_gui.services import app_updater
from hpc_gui.services.app_updater import (
    AUTOMATIC_INSTALL_STRATEGIES,
    download_and_verify_release,
    get_latest_release,
    is_newer_version,
    launch_update_installer,
)
from .widgets.login_widget import LoginWidget
from .widgets.jobs_outputs_widget import JobsOutputsWidget
from .widgets.directories_widget import DirectoriesWidget
from .widgets.ftp_widget import FtpWidget
from .widgets.editor_widget import EditorWidget
from .widgets.logs_widget import LogsWidget
from .dialogs.help_dialog import HelpDialog
from .dialogs.settings_dialog import SettingsDialog
from .dialogs.send_logs_dialog import SendLogsDialog
from hpc_gui.config.storage import (
    SBATCH_FOLLOW_MODE_NEW_TABS_SPLIT,
    SBATCH_FOLLOW_MODE_OUTPUTS_TAB,
    get_sbatch_follow_mode,
    get_squeue_auto_refresh_enabled,
)
from .dialogs.quick_tour import QuickTourOverlay
from .async_call import AsyncCall
from .splash_screen import UpdateSplash


class _BackgroundCall(QObject):
    finished = Signal(object)
    failed = Signal(str)
    done = Signal()
    progress = Signal(int, str, int, int)

    def __init__(self, fn):
        super().__init__()
        self._fn = fn
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        self._cancelled.set()

    @Slot()
    def run(self) -> None:
        try:
            self.finished.emit(self._fn(self.progress.emit, self._cancelled.is_set))
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.done.emit()


class MainWindow(QMainWindow):

    _logger = logging.getLogger("hpc_gui.ui.main_window")

    def changeEvent(self, event) -> None:  # type: ignore[override]
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange and hasattr(self, "jobs_outputs"):
            self.jobs_outputs.set_application_minimized(self.isMinimized())

    def _flag_icon(self, country_code: str) -> QIcon:
        """Return a small flag icon from packaged SVGs (stable on Windows)."""
        cc = (country_code or "").strip().lower()
        if cc == "en":
            cc = "gb"
        # Load SVG from: hpc_gui/assets/flags/{cc}.svg
        try:
            from pathlib import Path
            base = Path(__file__).resolve().parent.parent  # ui -> hpc_gui
            svg_path = base / "assets" / "flags" / f"{cc}.svg"
            if svg_path.exists():
                renderer = QSvgRenderer(str(svg_path))
                pm = QPixmap(18, 12)
                pm.fill(Qt.transparent)
                painter = QPainter(pm)
                renderer.render(painter)
                painter.end()
                return QIcon(pm)
        except Exception:
            pass

        # Fallback: simple colored badge (no text, no emoji)
        pm = QPixmap(18, 12)
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setBrush(QColor("#444" if cc != "tr" else "#E30A17"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(pm.rect().adjusted(0, 0, -1, -1), 2, 2)
        painter.end()
        return QIcon(pm)

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
        self.tabs.addTab(
            self.ftp,
            t("tabs.ftp") if t("tabs.ftp") != "[tabs.ftp]" else "FTP",
        )
        self.tabs.addTab(self.editor, t("tabs.editor"))
        self.tabs.addTab(self.logs, t("tabs.logs") if t("tabs.logs") != "[tabs.logs]" else "Logs")
        if is_source_run():
            telemetry = QApplication.instance().findChild(DebugTelemetry)
            if telemetry is not None:
                telemetry.observe_tab_widget(self.tabs, "main")
        self.tabs.currentChanged.connect(self._sync_command_polling)
        self.jobs_outputs.polling_visibility_changed.connect(
            self._sync_command_polling
        )

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

        self.jobs_outputs.request_show_directories.connect(self.show_directories)
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

    def run_shell_batch_in_terminal(self, script_paths: list[str]) -> None:
        commands = [f"bash {shlex.quote(path)}" for path in script_paths if path]
        if not commands:
            return
        self.tabs.setCurrentWidget(self.login)
        self.login.run_command_text("\n".join(commands))

    def run_shell_in_terminal(self, script_path: str) -> None:
        self.run_shell_batch_in_terminal([script_path])

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

    def _init_language_menu(self):
        """Semantic header: Menu / Plugins / Help with compact language + version."""
        menubar = self.menuBar()
        # --- Language menu (compact, directly accessible) ---
        self._lang_menu = QMenu(self)
        self._act_tr = QAction(self)
        self._act_en = QAction(self)
        self._act_tr.setCheckable(True)
        self._act_en.setCheckable(True)
        self._act_tr.setIcon(self._flag_icon("TR"))
        self._act_en.setIcon(self._flag_icon("GB"))
        self._act_tr.triggered.connect(lambda: self._switch_language("tr"))
        self._act_en.triggered.connect(lambda: self._switch_language("en"))
        self._lang_menu.addAction(self._act_tr)
        self._lang_menu.addAction(self._act_en)

        self._lang_btn = QToolButton(self)
        self._lang_btn.setPopupMode(QToolButton.InstantPopup)
        self._lang_btn.setMenu(self._lang_menu)
        self._lang_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._lang_btn.setIconSize(QSize(20, 14))
        # Compact selector – no wide minimum that crowds the header
        self._lang_btn.setStyleSheet(
            "QToolButton { padding: 4px 8px; text-align: left; }"
            "QToolButton::menu-indicator { subcontrol-position: right center; }"
        )

        self._version_label = QLabel(f"v{__version__}")
        self._version_label.setStyleSheet(
            "QLabel { color: #555; padding: 0 8px; font-weight: 600; }"
        )

        # --- Menu ---
        self._menu_menu = menubar.addMenu(t("menu.menu"))
        self._act_settings = QAction(t("menu.settings"), self)
        self._act_settings.triggered.connect(self._open_settings)
        self._menu_menu.addAction(self._act_settings)
        self._act_check_updates = QAction(t("menu.check_updates"), self)
        self._act_check_updates.triggered.connect(lambda: self._check_for_updates(manual=True))
        self._menu_menu.addAction(self._act_check_updates)
        # Command Palette only if a REAL implementation exists – omit the fake Help wiring
        # No visible Command Palette entry when none exists; Help stays on F1.
        self._menu_menu.addSeparator()
        self._act_exit = QAction(t("menu.exit"), self)
        self._act_exit.triggered.connect(self.close)
        self._menu_menu.addAction(self._act_exit)

        # --- Plugins ---
        self._plugins_menu = menubar.addMenu(t("menu.plugins"))
        self._act_plugins_discover = QAction(t("menu.browse_install"), self)
        self._act_plugins_discover.triggered.connect(lambda: self._open_plugins(initial_tab="discover"))
        self._plugins_menu.addAction(self._act_plugins_discover)
        self._act_plugins_installed = QAction(t("menu.manage_installed"), self)
        self._act_plugins_installed.triggered.connect(lambda: self._open_plugins(initial_tab="installed"))
        self._plugins_menu.addAction(self._act_plugins_installed)
        self._act_plugins_updates = QAction(t("menu.check_plugin_updates"), self)
        self._act_plugins_updates.triggered.connect(lambda: self._open_plugins(initial_tab="updates"))
        self._plugins_menu.addAction(self._act_plugins_updates)
        self._plugins_menu.addSeparator()
        # Dynamic plugin roots will be inserted here
        self._plugins_dynamic_separator_top = None
        # Keep a reference to the bottom separator/action for insertion point
        self._plugins_dynamic_before = None
        self._plugins_menu.addSeparator()
        self._act_request_plugin = QAction(t("menu.request_plugin"), self)
        self._act_request_plugin.triggered.connect(self._open_plugin_requests)
        self._plugins_menu.addAction(self._act_request_plugin)
        # Capture insertion point: dynamic roots go before the last separator + Request
        # The separator added above is the bottom separator
        all_actions = self._plugins_menu.actions()
        # bottom separator is second-to-last before Request; we want to insert before it
        if len(all_actions) >= 2:
            # actions: [discover, installed, updates, sep1, sep2(dynamic-top? actually we added sep then sep?), request]
            # We added: discover, installed, updates, sep(static), sep(bottom), request
            # Dynamic should be between those two seps: so before bottom sep
            self._plugins_dynamic_before = all_actions[-2]  # bottom sep
        self._plugins_dynamic_separator_top = all_actions[3] if len(all_actions) > 3 else None

        # --- Help ---
        self._help_menu = menubar.addMenu(t("menu.help"))
        self._act_help_center = QAction(t("menu.help_center"), self)
        try:
            from PySide6.QtGui import QKeySequence
            self._act_help_center.setShortcut(QKeySequence("F1"))
        except Exception:
            pass
        self._act_help_center.triggered.connect(self._open_help)
        self._help_menu.addAction(self._act_help_center)
        # Quick Tour if existing path is real/usable
        self._act_quick_tour = None
        try:
            from hpc_gui.ui.dialogs.quick_tour import QuickTourOverlay  # noqa: F401
            self._act_quick_tour = QAction(t("menu.quick_tour"), self)
            self._act_quick_tour.triggered.connect(self.start_quick_tour)
            self._help_menu.addAction(self._act_quick_tour)
        except Exception:
            self._act_quick_tour = None
        self._help_menu.addSeparator()
        self._act_send_logs = QAction(t("menu.send_logs"), self)
        self._act_send_logs.triggered.connect(self._open_send_logs)
        self._help_menu.addAction(self._act_send_logs)
        self._help_menu.addSeparator()
        self._act_about = QAction(t("menu.about"), self)
        self._act_about.triggered.connect(self._open_about)
        self._help_menu.addAction(self._act_about)

        # --- Compact upper-right utilities: language + plain version text ---
        lang_container = QWidget(self)
        lang_container.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        layout = QHBoxLayout(lang_container)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.addWidget(self._lang_btn)
        layout.addWidget(self._version_label)
        menubar.setCornerWidget(lang_container, Qt.TopRightCorner)

        # Plugin menu dynamic handling
        self._plugin_contributions: list = []
        self._plugins_dynamic_actions: list = []
        self._refresh_plugin_contributions_cache()
        try:
            self._plugins_menu.aboutToShow.connect(self._rebuild_plugins_menu_dynamic)
        except Exception:
            pass

    def _asset_svg_icon(self, rel_path: str, w: int = 18, h: int = 18) -> QIcon:
        """Render an SVG asset into a QIcon (stable across platforms)."""
        try:
            from pathlib import Path
            base = Path(__file__).resolve().parent.parent  # ui -> hpc_gui
            svg_path = base / rel_path
            if svg_path.exists():
                renderer = QSvgRenderer(str(svg_path))
                pm = QPixmap(w, h)
                pm.fill(Qt.transparent)
                painter = QPainter(pm)
                renderer.render(painter)
                painter.end()
                return QIcon(pm)
        except Exception:
            pass
        return QIcon()

    def _open_help(self):
        try:
            dlg = HelpDialog(self)
            dlg.exec()
        except Exception:
            pass

    def _open_settings(self):
        try:
            dlg = SettingsDialog(
                self,
                session=getattr(self, "_session", None),
                update_remote_defaults=self.login.update_active_profile_remote_defaults,
                clear_remote_directory_cache=self.ftp.clear_remote_directory_caches,
            )
            dlg.exec()
            self.jobs_outputs.apply_refresh_settings()
            self._sync_command_polling()
            self.ftp.apply_settings()
        except Exception:
            pass

    def _open_send_logs(self):
        try:
            dlg = SendLogsDialog(self, crash_context=False)
            dlg.exec()
        except Exception:
            pass

    def _open_about(self):
        try:
            from hpc_gui.ui.dialogs.about_dialog import AboutDialog
            dlg = AboutDialog(self)
            dlg.exec()
        except Exception:
            pass

    def _open_plugin_requests(self):
        try:
            from hpc_gui.ui.dialogs.plugin_manager_dialog import PLUGIN_REQUEST_URL, PluginManagerDialog
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            url = PLUGIN_REQUEST_URL
            if PluginManagerDialog._is_allowed_plugin_request_url(url):
                opened = QDesktopServices.openUrl(QUrl(url))
                if not opened:
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, t("plugins.dialog_title"), t("plugins.request_plugin_failed"))
            else:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, t("plugins.dialog_title"), t("plugins.request_plugin_failed"))
        except Exception:
            pass

    def _open_plugins(self, initial_tab="discover"):
        try:
            from hpc_gui.ui.dialogs.plugin_manager_dialog import PluginManagerDialog
            dlg = PluginManagerDialog(self, initial_tab=initial_tab)
            # Live refresh without restart
            try:
                dlg.plugins_changed.connect(self._on_plugins_changed)
            except Exception:
                pass
            dlg.exec()
            # Post-exec safety refresh
            self._refresh_plugin_contributions_cache()
        except Exception as exc:
            self._logger.exception("Opening the Plugin Manager failed")
            show_exception(
                self,
                title=t("plugins.dialog_title"),
                user_message=t("plugins.open_failed"),
                exc=exc,
                area="PLUGINS",
            )

    def _on_plugins_changed(self):
        try:
            self._refresh_plugin_contributions_cache()
        except Exception:
            pass

    def _refresh_plugin_contributions_cache(self):
        try:
            from hpc_gui.plugins.loader import load_installed_plugins
            from hpc_gui.plugins.ui_contributions import collect_plugin_menu_contributions
            # Collect only from enabled/compatible/corrupt-filtered plugins
            result = load_installed_plugins()
            # Filter disabled already done by loader; but we also need to keep only those with contribution
            self._plugin_contributions = collect_plugin_menu_contributions(result.plugins)
        except Exception as exc:
            self._logger.warning("Failed to refresh plugin contributions: %s", exc, exc_info=exc)
            self._plugin_contributions = []

    def _current_menu_context(self):
        try:
            from hpc_gui.plugins.ui_contributions import MenuContext
            from hpc_gui.core.i18n import current_language
            sess = getattr(self, "_session", None)
            connected = bool(sess and sess.get("connected")) if isinstance(sess, dict) else False
            editor_active = False
            try:
                editor_active = self.tabs.currentWidget() is self.editor
            except Exception:
                pass
            file_selected = False
            try:
                # Heuristic: if directories or ftp has selection
                if hasattr(self, "directories") and hasattr(self.directories, "panel_scratch"):
                    pnl = self.directories.panel_scratch
                    if hasattr(pnl, "tree") and hasattr(pnl.tree, "selectedItems"):
                        file_selected = bool(pnl.tree.selectedItems())
            except Exception:
                pass
            return MenuContext(connected=connected, editor_active=editor_active, file_selected=file_selected, language=current_language())
        except Exception:
            from hpc_gui.plugins.ui_contributions import MenuContext
            return MenuContext()

    def _rebuild_plugins_menu_dynamic(self):
        """Evaluate when-conditions on menu open, not on every tab change."""
        try:
            from hpc_gui.plugins.ui_contributions import evaluate_when, get_display_label
            from PySide6.QtGui import QAction
            from PySide6.QtWidgets import QMenu
            # Clear prior dynamic
            for act in list(getattr(self, "_plugins_dynamic_actions", [])):
                try:
                    self._plugins_menu.removeAction(act)
                    # If it's a menu's action, also delete menu
                    menu = act.menu() if hasattr(act, "menu") else None
                    if menu is not None:
                        menu.deleteLater()
                except Exception:
                    pass
            self._plugins_dynamic_actions = []
            ctx = self._current_menu_context()
            if not getattr(self, "_plugin_contributions", None):
                # No contributions at all -> still need to update separator visibility
                try:
                    has_any = False
                    if hasattr(self, "_plugins_dynamic_separator_top") and self._plugins_dynamic_separator_top is not None:
                        self._plugins_dynamic_separator_top.setVisible(has_any)
                    if hasattr(self, "_plugins_dynamic_before") and self._plugins_dynamic_before is not None:
                        self._plugins_dynamic_before.setVisible(True)
                except Exception:
                    pass
                return
            
            insert_before = getattr(self, "_plugins_dynamic_before", None)
            for contrib in sorted(self._plugin_contributions, key=lambda c: (get_display_label(c.label, c.labels, ctx.language).casefold(), c.label.casefold(), c.plugin_id.casefold())):
                lang = ctx.language
                root_label = get_display_label(contrib.label, contrib.labels, lang)
                # Create root menu for this plugin
                root_menu = QMenu(root_label, self)
                # For each item in contribution (preserve order)
                has_visible = False
                for item in contrib.items:
                    from hpc_gui.plugins.ui_contributions import PluginMenuAction, PluginMenuSeparator, PluginMenuSubmenu
                    if isinstance(item, PluginMenuSeparator):
                        # Separators inside root: only add if there is a previous non-separator and not at end – but normalization already handled
                        sep_act = QAction(self)
                        sep_act.setSeparator(True)
                        root_menu.addAction(sep_act)
                        has_visible = True
                        continue
                    if isinstance(item, PluginMenuSubmenu):
                        # Evaluate submenu when
                        caps = frozenset(self._get_plugin_capabilities(contrib.plugin_id))
                        show = evaluate_when(item.when, ctx, caps)
                        if not show:
                            if item.unavailable == "hide":
                                continue
                            # disable – show but disabled
                        sub_label = get_display_label(item.label, item.labels, lang)
                        sub_menu = QMenu(sub_label, self)
                        if not show and item.unavailable == "disable":
                            sub_menu.setEnabled(False)
                        # Add inner actions/separators
                        inner_visible = False
                        for child in item.items:
                            if isinstance(child, PluginMenuSeparator):
                                sep = QAction(self)
                                sep.setSeparator(True)
                                sub_menu.addAction(sep)
                                inner_visible = True
                                continue
                            if isinstance(child, PluginMenuAction):
                                caps2 = caps
                                cond_ok = evaluate_when(child.when, ctx, caps2)
                                if not cond_ok and child.unavailable == "hide":
                                    continue
                                a_label = get_display_label(child.label, child.labels, lang)
                                act = QAction(a_label, self)
                                if not cond_ok and child.unavailable == "disable":
                                    act.setEnabled(False)
                                # Check allowlist and capability guard before enabling
                                from hpc_gui.services.plugin_menu_actions import can_execute_action
                                # Resolve owning plugin object for dispatch
                                owning = self._find_installed_plugin(contrib.plugin_id)
                                if owning is not None:
                                    allowed, _reason = can_execute_action(child.action, owning)
                                    if not allowed:
                                        act.setEnabled(False)
                                else:
                                    act.setEnabled(False)
                                # Capture for dispatcher: host-owned action, pass owning plugin from host
                                act.triggered.connect(lambda _checked=False, a=child.action, p=contrib.plugin_id: self._dispatch_plugin_action(a, p))
                                sub_menu.addAction(act)
                                inner_visible = True
                                has_visible = True
                            else:
                                continue
                        if inner_visible:
                            # Normalize separators inside submenu already done
                            root_menu.addMenu(sub_menu)
                            has_visible = True
                        else:
                            sub_menu.deleteLater()
                            continue
                    elif isinstance(item, PluginMenuAction):
                        caps = frozenset(self._get_plugin_capabilities(contrib.plugin_id))
                        cond_ok = evaluate_when(item.when, ctx, caps)
                        if not cond_ok and item.unavailable == "hide":
                            continue
                        a_label = get_display_label(item.label, item.labels, lang)
                        act = QAction(a_label, self)
                        if not cond_ok and item.unavailable == "disable":
                            act.setEnabled(False)
                        from hpc_gui.services.plugin_menu_actions import can_execute_action
                        owning = self._find_installed_plugin(contrib.plugin_id)
                        if owning is not None:
                            allowed, _reason = can_execute_action(item.action, owning)
                            if not allowed:
                                act.setEnabled(False)
                        else:
                            act.setEnabled(False)
                        act.triggered.connect(lambda _checked=False, a=item.action, p=contrib.plugin_id: self._dispatch_plugin_action(a, p))
                        root_menu.addAction(act)
                        has_visible = True
                if has_visible:
                    # Insert before bottom separator
                    if insert_before is not None:
                        self._plugins_menu.insertMenu(insert_before, root_menu)
                        # Keep action reference for removal
                        self._plugins_dynamic_actions.append(root_menu.menuAction())
                    else:
                        action = self._plugins_menu.addMenu(root_menu)
                        self._plugins_dynamic_actions.append(action)
                else:
                    root_menu.deleteLater()
            # Separator visibility: exactly one when no visible dynamic roots
            try:
                has_any = len(self._plugins_dynamic_actions) > 0
                if hasattr(self, "_plugins_dynamic_separator_top") and self._plugins_dynamic_separator_top is not None:
                    self._plugins_dynamic_separator_top.setVisible(has_any)
                if hasattr(self, "_plugins_dynamic_before") and self._plugins_dynamic_before is not None:
                    self._plugins_dynamic_before.setVisible(True)
            except Exception:
                pass
        except Exception as exc:
            self._logger.warning("Failed to rebuild Plugins menu: %s", exc, exc_info=exc)

    def _get_plugin_capabilities(self, plugin_id: str) -> tuple[str, ...]:
        try:
            for contrib in getattr(self, "_plugin_contributions", []):
                if contrib.plugin_id == plugin_id:
                    # Need owning plugin's capabilities
                    p = self._find_installed_plugin(plugin_id)
                    if p:
                        return tuple(p.manifest.capabilities or ())
            # fallback
            from hpc_gui.plugins.loader import load_installed_plugins
            result = load_installed_plugins()
            for inst in result.plugins:
                if inst.manifest.id == plugin_id:
                    return tuple(inst.manifest.capabilities or ())
        except Exception:
            pass
        return ()

    def _find_installed_plugin(self, plugin_id: str):
        try:
            from hpc_gui.plugins.loader import load_installed_plugins
            res = load_installed_plugins()
            for inst in res.plugins:
                if inst.manifest.id == plugin_id:
                    return inst
        except Exception:
            pass
        return None

    def _dispatch_plugin_action(self, action: str, plugin_id: str):
        try:
            from hpc_gui.services.plugin_menu_actions import dispatch_plugin_menu_action
            from hpc_gui.ui.plugin_menu_qt_host import QtPluginMenuHost

            plugin = self._find_installed_plugin(plugin_id)
            if plugin is None:
                self._logger.warning("Plugin %s not found for action %s", plugin_id, action)
                return
            host = QtPluginMenuHost(editor_widget=getattr(self, "editor", None), host_window=self)
            dispatch_plugin_menu_action(action, plugin, host)
        except Exception as exc:
            self._logger.warning("Dispatch of %r for %s failed: %s", action, plugin_id, exc, exc_info=exc)

    def _show_startup_changelog_if_needed(self) -> None:
        try:
            if get_last_seen_changelog_version() == __version__:
                return
            text = chronological_changelog(load_changelog_text())
            if not text:
                set_last_seen_changelog_version(__version__)
                return
            self._show_changelog_dialog(text)
            set_last_seen_changelog_version(__version__)
        except Exception:
            try:
                set_last_seen_changelog_version(__version__)
            except Exception:
                pass

    def _show_changelog_dialog(self, changelog_text: str) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(t("updates.changelog_title").format(version=__version__))
        dialog.resize(820, 640)

        layout = QVBoxLayout(dialog)
        text = QTextEdit(dialog)
        text.setReadOnly(True)
        text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        text.setMarkdown(changelog_text)
        layout.addWidget(text, 1)

        close_btn = QPushButton(t("common.close"), dialog)
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
        dialog.exec()

    def _show_update_progress(self, value: int, status_key: str) -> None:
        if self._update_progress is None:
            dialog = UpdateSplash(self)
            dialog.setWindowModality(Qt.WindowModality.WindowModal)
            dialog.rejected.connect(self._cancel_update_jobs)
            self._update_progress = dialog
        self._on_update_progress(value, status_key)
        self._update_progress.show()

    def _on_update_progress(
        self, value: int, status_key: str, downloaded: int = 0, total: int = 0
    ) -> None:
        if self._update_progress is None:
            return
        label = {
            "checking": "Checking for updates...",
            "preparing": "Preparing download...",
            "downloading": "Downloading update...",
            "verifying": "Verifying downloaded file...",
            "ready": "Update is ready to install.",
            "installing": "Installing update...",
        }.get(status_key, status_key)
        self._update_progress.set_status(label, value, downloaded, total)

    def _close_update_progress(self) -> None:
        if self._update_progress is not None:
            self._update_progress.hide()
            self._update_progress.deleteLater()
            self._update_progress = None

    def _cancel_update_jobs(self) -> None:
        self._update_cancelled = True
        for worker in self._update_workers.values():
            worker.cancel()
        self._close_update_progress()

    def _run_update_job(self, fn, on_success) -> None:
        self._update_cancelled = False
        thread = QThread(self)
        worker = _BackgroundCall(fn)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(on_success)
        worker.failed.connect(self._on_update_error)
        worker.progress.connect(self._on_update_progress)
        worker.done.connect(thread.quit)
        worker.done.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda current=thread: self._update_job_finished(current))
        self._update_jobs.add(thread)
        self._update_workers[thread] = worker
        self._update_busy_count += 1
        if hasattr(self, "_act_check_updates"):
            self._act_check_updates.setEnabled(False)
        thread.start()

    def _update_job_finished(self, thread: QThread) -> None:
        self._update_jobs.discard(thread)
        self._update_workers.pop(thread, None)
        self._update_busy_count = max(0, self._update_busy_count - 1)
        if self._update_busy_count == 0:
            if hasattr(self, "_act_check_updates"):
                self._act_check_updates.setEnabled(True)

    def _check_for_updates(self, manual: bool = True) -> None:
        if self._update_busy_count:
            return
        self._update_manual = manual
        self._update_interactive = manual
        if manual:
            self._show_update_progress(5, "checking")
        self._run_update_job(
            lambda progress, _cancelled: get_latest_release(),
            self._on_release_checked,
        )

    def _on_release_checked(self, release) -> None:
        if self._update_cancelled:
            self._close_update_progress()
            return
        if not is_newer_version(release.version, __version__):
            self._close_update_progress()
            if self._update_manual:
                QMessageBox.information(
                    self,
                    t("updates.title"),
                    t("updates.up_to_date").format(version=__version__),
                )
            return

        self._update_interactive = True
        if not is_frozen_exe():
            self._close_update_progress()
            QMessageBox.information(
                self,
                t("updates.title"),
                t("updates.source_mode").format(version=release.version),
            )
            if release.html_url:
                webbrowser.open(release.html_url)
            return

        macos_auto_supported = not (
            release.install_strategy == "macos-bundle"
            and release.security_status != app_updater.SECURITY_SIGNED
        )
        if release.install_strategy not in AUTOMATIC_INSTALL_STRATEGIES or not macos_auto_supported:
            self._close_update_progress()
            message = t("updates.manual_install").format(version=release.version)
            if current_os() == "macos":
                security_key = {
                    app_updater.SECURITY_UNSIGNED: "updates.security_unsigned_mac",
                    app_updater.SECURITY_SIGNED: "updates.security_signed_mac",
                    app_updater.SECURITY_UNKNOWN: "updates.security_unknown_mac",
                }.get(release.security_status, "updates.security_unknown_mac")
                message += "\n\n" + t(security_key)
            QMessageBox.information(
                self,
                t("updates.title"),
                message,
            )
            webbrowser.open(release.zip_url or release.html_url)
            return

        self._close_update_progress()
        answer = QMessageBox.question(
            self,
            t("updates.available_title"),
            t("updates.available_message").format(
                current=__version__,
                latest=release.version,
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._show_update_progress(0, "preparing")
        QApplication.processEvents()
        self._run_update_job(
            lambda progress, cancelled: (
                release,
                download_and_verify_release(release, progress_cb=progress, cancelled=cancelled),
            ),
            self._on_update_downloaded,
        )

    def _on_update_downloaded(self, result) -> None:
        if self._update_cancelled:
            self._close_update_progress()
            return
        release, zip_path = result
        self._close_update_progress()
        answer = QMessageBox.question(
            self,
            t("updates.ready_title"),
            t("updates.ready_message").format(version=release.version),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self._show_update_progress(0, "preparing")
            QApplication.processEvents()
            launch_update_installer(zip_path, release.version, release.install_strategy)
        except Exception as exc:
            self._on_update_error(str(exc))
            return
        QApplication.quit()

    def _on_update_error(self, message: str) -> None:
        if self._update_cancelled:
            self._close_update_progress()
            return
        self._close_update_progress()
        if not self._update_interactive:
            return
        QMessageBox.critical(
            self,
            t("updates.error_title"),
            t("updates.error_message").format(error=message),
        )

    def start_quick_tour(self):
        try:
            overlay = QuickTourOverlay(self)
            overlay.show()
        except Exception:
            pass

    def _switch_language(self, lang: str):
        set_language(lang)
        self.retranslate_ui()

    def retranslate_ui(self):
        # Window + tabs
        self.setWindowTitle(t("app.title"))
        if hasattr(self, "tabs"):
            self.tabs.setTabText(self.tabs.indexOf(self.login), t("tabs.login"))
            self.tabs.setTabText(self.tabs.indexOf(self.jobs_outputs), t("tabs.jobs_outputs"))
            self.tabs.setTabText(self.tabs.indexOf(self.directories), t("tabs.directories"))
            self.tabs.setTabText(
                self.tabs.indexOf(self.ftp),
                t("tabs.ftp") if t("tabs.ftp") != "[tabs.ftp]" else "FTP",
            )
            self.tabs.setTabText(self.tabs.indexOf(self.editor), t("tabs.editor"))
            self.tabs.setTabText(self.tabs.indexOf(self.logs), t("tabs.logs"))

        # Menus
        if hasattr(self, "_menu_menu"):
            self._menu_menu.setTitle(t("menu.menu"))
        if hasattr(self, "_act_settings"):
            self._act_settings.setText(t("menu.settings"))
        if hasattr(self, "_act_check_updates"):
            self._act_check_updates.setText(t("menu.check_updates"))
        if hasattr(self, "_act_exit"):
            self._act_exit.setText(t("menu.exit"))
        if hasattr(self, "_plugins_menu"):
            self._plugins_menu.setTitle(t("menu.plugins"))
        if hasattr(self, "_act_plugins_discover"):
            self._act_plugins_discover.setText(t("menu.browse_install"))
        if hasattr(self, "_act_plugins_installed"):
            self._act_plugins_installed.setText(t("menu.manage_installed"))
        if hasattr(self, "_act_plugins_updates"):
            self._act_plugins_updates.setText(t("menu.check_plugin_updates"))
        if hasattr(self, "_act_request_plugin"):
            self._act_request_plugin.setText(t("menu.request_plugin"))
        if hasattr(self, "_help_menu"):
            self._help_menu.setTitle(t("menu.help"))
        if hasattr(self, "_act_help_center"):
            self._act_help_center.setText(t("menu.help_center"))
        if hasattr(self, "_act_quick_tour") and self._act_quick_tour is not None:
            self._act_quick_tour.setText(t("menu.quick_tour"))
        if hasattr(self, "_act_send_logs"):
            self._act_send_logs.setText(t("menu.send_logs"))
        if hasattr(self, "_act_about"):
            self._act_about.setText(t("menu.about"))
        # Language menu labels / selected language display
        if hasattr(self, "_act_tr"):
            self._act_tr.setText(t("language.turkish"))
        if hasattr(self, "_act_en"):
            self._act_en.setText(t("language.english"))
        # Button shows currently selected language (with flag) and is compact
        if hasattr(self, "_lang_btn"):
            cur = getattr(self, "_current_lang", None)
            if cur is None:
                from hpc_gui.core.i18n import current_language as _cur_lang
                cur = _cur_lang()
            if cur == "tr":
                self._lang_btn.setIcon(self._flag_icon("TR"))
                self._lang_btn.setText(t("language.turkish"))
                if hasattr(self, "_act_tr"):
                    self._act_tr.setChecked(True)
                if hasattr(self, "_act_en"):
                    self._act_en.setChecked(False)
            else:
                self._lang_btn.setIcon(self._flag_icon("GB"))
                self._lang_btn.setText(t("language.english"))
                if hasattr(self, "_act_tr"):
                    self._act_tr.setChecked(False)
                if hasattr(self, "_act_en"):
                    self._act_en.setChecked(True)
            self._lang_btn.setToolTip(t("language.menu_title"))
        # Rebuild plugin menu to retranslate dynamic labels without restart
        try:
            self._refresh_plugin_contributions_cache()
            self._rebuild_plugins_menu_dynamic()
        except Exception:
            pass

        # Ask children to retranslate if they support it
        for w in (
            getattr(self, "login", None),
            getattr(self, "jobs_outputs", None),
            getattr(self, "directories", None),
            getattr(self, "ftp", None),
            getattr(self, "editor", None),
            getattr(self, "logs", None),
        ):
            if w is not None and hasattr(w, "retranslate_ui"):
                try:
                    w.retranslate_ui()
                except Exception:
                    pass

    def on_session_changed(self, session):
        self._job_poll_generation += 1
        self._job_poll_worker = None
        self._session = session
        self._last_job_ids = set()
        self._job_monitor_initialized = False
        self.jobs_outputs.set_session(session)
        self.directories.set_session(session)
        self.ftp.set_session(session)
        self.editor.set_session(session)
        self._sync_command_polling()

    def _sync_command_polling(self, _index: int = -1) -> None:
        if not hasattr(self, "tabs") or not hasattr(self, "jobs_outputs"):
            return
        page_active = self.tabs.currentWidget() is self.jobs_outputs
        self.jobs_outputs.set_page_active(page_active)
        session = getattr(self, "_session", None)
        should_poll_jobs = bool(
            session
            and session.get("connected")
            and self.jobs_outputs.is_details_polling_visible()
            and get_squeue_auto_refresh_enabled()
        )
        if should_poll_jobs:
            self.job_timer.start()
            self._poll_jobs()
        else:
            self.job_timer.stop()

    def show_directories(self):
        idx = self.tabs.indexOf(self.directories)
        if idx >= 0:
            self.tabs.setCurrentIndex(idx)

    def open_in_editor(self, path: str, content: str):
        self.editor.open_file(path, content)
        idx = self.tabs.indexOf(self.editor)
        if idx >= 0:
            self.tabs.setCurrentIndex(idx)

    def open_in_editor_new_window(self, path: str, content: str):
        """Open a standalone, visible editor window for a remote file."""
        editor = EditorWidget()
        editor.set_session(getattr(self, "_session", None))
        editor.open_file(path, content)
        window = QMainWindow(self, Qt.WindowType.Window)
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        window.setWindowTitle(f"{t('tabs.editor')}: {path.rsplit('/', 1)[-1] or path}")
        window.setCentralWidget(editor)
        window.resize(1000, 700)
        self._editor_windows.append(window)
        window_token = id(window)

        def cleanup(*_args):
            self._editor_windows[:] = [
                candidate
                for candidate in self._editor_windows
                if id(candidate) != window_token
            ]

        window.destroyed.connect(cleanup)
        window.show()
        window.raise_()
        window.activateWindow()
        return window

    def open_local_in_editor(self, path: str, new_window: bool = False):
        """Open a local filesystem file in the in-app editor (no session)."""
        from PySide6.QtWidgets import QMessageBox

        try:
            content = Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logging.getLogger("hpc_gui.ui.main_window").warning(
                "Could not open local file for editing: %s", path, exc_info=exc
            )
            QMessageBox.warning(
                self,
                t("common.error"),
                f"{type(exc).__name__}: {exc}",
            )
            return
        if new_window:
            editor = EditorWidget()
            editor.open_file(path, content, is_local=True)
            window = QMainWindow(self, Qt.WindowType.Window)
            window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
            window.setWindowTitle(f"{t('tabs.editor')}: {Path(path).name or path}")
            window.setCentralWidget(editor)
            window.resize(1000, 700)
            self._editor_windows.append(window)
            window_token = id(window)

            def cleanup(*_args):
                self._editor_windows[:] = [
                    candidate
                    for candidate in self._editor_windows
                    if id(candidate) != window_token
                ]

            window.destroyed.connect(cleanup)
            window.show()
            window.raise_()
            window.activateWindow()
            return window
        self.editor.open_file(path, content, is_local=True)
        idx = self.tabs.indexOf(self.editor)
        if idx >= 0:
            self.tabs.setCurrentIndex(idx)
        return None

    def on_script_submitted(self, job_id: str, script_path: str):
        try:
            follow_mode = get_sbatch_follow_mode()
            show_jobs_page = follow_mode in {
                SBATCH_FOLLOW_MODE_OUTPUTS_TAB,
                SBATCH_FOLLOW_MODE_NEW_TABS_SPLIT,
            }
            if show_jobs_page:
                idx = self.tabs.indexOf(self.jobs_outputs)
                if idx >= 0:
                    self.tabs.setCurrentIndex(idx)
            if hasattr(self.jobs_outputs, "focus_job"):
                self.jobs_outputs.focus_job(
                    job_id,
                    script_path,
                    switch_to_outputs=show_jobs_page,
                    follow_mode=follow_mode,
                )
        except Exception:
            pass

    def _poll_jobs(self):
        # Runs periodically while Job Details is visible; reports finished jobs.
        if not self.jobs_outputs.is_details_polling_visible():
            self.job_timer.stop()
            return
        if self._job_poll_worker is not None:
            return
        session = getattr(self, "_session", None)
        if not session or not session.get("connected"):
            return
        ssh = session.get("ssh")
        slurm = session.get("slurm")
        cfg = session.get("cfg")
        if not ssh or not slurm or not cfg:
            return
        previous_ids = set(self._last_job_ids)
        initialized = self._job_monitor_initialized
        generation = self._job_poll_generation

        def fetch():
            out = slurm.active_job_ids(cfg.username)
            job_ids = {
                line.strip()
                for line in out.splitlines()
                if line.strip().isdigit()
            }
            states = {}
            if initialized:
                for jid in previous_ids - job_ids:
                    try:
                        state_out = slurm.job_state(jid)
                        states[jid] = next(
                            (
                                line.split("|", 1)[0].strip().split("+", 1)[0]
                                for line in state_out.splitlines()
                                if line.strip()
                            ),
                            "",
                        )
                    except Exception:
                        states[jid] = ""
            return job_ids, states

        worker = AsyncCall(generation, fetch)
        self._job_poll_worker = worker

        def failed(token, _exc) -> None:
            if self._job_poll_worker is worker:
                self._job_poll_worker = None

        def finished(token, result) -> None:
            if self._job_poll_worker is worker:
                self._job_poll_worker = None
            if token != self._job_poll_generation:
                return
            job_ids, states = result
            if not self._job_monitor_initialized:
                self._last_job_ids = job_ids
                self._job_monitor_initialized = True
                return
            self._show_finished_jobs(states)
            self._last_job_ids = job_ids

        worker.signals.failed.connect(failed)
        worker.signals.finished.connect(finished)
        QThreadPool.globalInstance().start(worker)

    def _show_finished_jobs(self, states: dict[str, str]) -> None:
        for jid in sorted(states):
            state = states[jid]
            if state == "COMPLETED":
                message = t("login.job_completed").format(jobid=jid)
            elif state:
                message = t("login.job_failed").format(jobid=jid, state=state)
            else:
                message = t("login.job_finished").format(jobid=jid)
            self.login.append_console(message)
            if self._job_tray:
                self._job_tray.showMessage(
                    t("login.job_notification_title"),
                    message,
                    QSystemTrayIcon.MessageIcon.Information,
                    8000,
                )

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
