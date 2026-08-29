# ruff: noqa: E402  (Qt imports intentionally follow the graphics bootstrap)
import sys
import os
import logging
import subprocess
from hpc_gui.config.storage import load_settings
from hpc_gui.core.terminal_graphics import (
    GbmWarningTracker,
    apply_bootstrap,
    restart_command,
    restart_environment,
)

# This import must stay before any Qt/WebEngine import: the Chromium flags are
# selected during bootstrap, not after QApplication has initialized Qt.
GRAPHICS_BOOTSTRAP = apply_bootstrap(load_settings())
_GBM_TRACKER = GbmWarningTracker()
_gbm_suggestion_pending = False

from PySide6.QtCore import qInstallMessageHandler
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon
from pathlib import Path

from hpc_gui.core.i18n import load_saved_language, system_default_language
from hpc_gui.core.i18n import t, validate_language_files
from hpc_gui.core.logging_setup import setup_logging, install_crash_logging, install_excepthook
from hpc_gui.core.debug_support import log_startup_snapshot
from hpc_gui.core.debug_telemetry import DebugTelemetry, is_source_run
from hpc_gui.core.crash_reporter import read_crash_flag, clear_crash_flag
from hpc_gui.ui.main_window import MainWindow
from hpc_gui.config.storage import get_ui_pref_bool, set_ui_pref_bool, update_settings
from hpc_gui.ui.dialogs.welcome_dialog import WelcomeDialog
from hpc_gui.ui.splash_screen import StartupSplash


def _performance_probe():
    return sys.modules.get("_hpc_gui_perf_probe")


def _performance_mark(name: str) -> None:
    probe = _performance_probe()
    if probe is not None:
        try:
            probe.mark(name)
        except Exception:
            pass


def _set_application_icon(app: QApplication) -> None:
    """Use the release icon for the app window and taskbar entry too."""
    candidates = [
        Path(__file__).resolve().parents[2] / "build" / "macos" / "hpc-client-gui.icns",
        Path(__file__).resolve().parents[2] / "build" / "windows" / "hpc-client-gui.ico",
        Path(getattr(sys, "_MEIPASS", "")) / "hpc_gui" / "assets" / "hpc-client-gui.icns",
        Path(getattr(sys, "_MEIPASS", "")) / "hpc_gui" / "assets" / "hpc-client-gui.ico",
    ]
    for icon_path in candidates:
        if icon_path.is_file():
            app.setWindowIcon(QIcon(str(icon_path)))
            return


def _configure_application_identity(app: QApplication) -> None:
    app.setApplicationName("HPC Client GUI")
    app.setApplicationDisplayName("HPC Client GUI")
    app.setOrganizationName("mskomek")
    app.setOrganizationDomain("github.com")


def _bootstrap_safety_checks() -> None:
    """Best-effort startup guards.

    - Detect i18n key drift (logs only)
    - Cleanup stale/orphan external process records (logs only)
    """
    try:
        validate_language_files()
    except Exception:
        pass
    try:
        from hpc_gui.services.process_registry import cleanup_orphans

        cleanup_orphans(aggressive=True)
    except Exception:
        pass


def _qt_message_handler(mode, context, message) -> None:
    """Keep Qt logging and forward only measured GBM evidence to the GUI."""
    del context
    logging.getLogger("hpc_gui.qt").error("Qt message type=%s: %s", mode, message)
    global _gbm_suggestion_pending
    if GRAPHICS_BOOTSTRAP.mode == "auto" and not GRAPHICS_BOOTSTRAP.applied_disable_gpu:
        if _GBM_TRACKER.record(str(message)):
            _gbm_suggestion_pending = True


def _offer_graphics_compatibility(window: MainWindow) -> None:
    global _gbm_suggestion_pending
    if not _gbm_suggestion_pending:
        return
    _gbm_suggestion_pending = False
    if GRAPHICS_BOOTSTRAP.mode != "auto" or GRAPHICS_BOOTSTRAP.applied_disable_gpu:
        return
    box = QMessageBox(window)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(t("graphics.suggestion_title"))
    box.setText(t("graphics.suggestion_message"))
    enable_restart = box.addButton(t("graphics.enable_restart"), QMessageBox.ButtonRole.AcceptRole)
    enable_later = box.addButton(t("graphics.enable_later"), QMessageBox.ButtonRole.DestructiveRole)
    box.addButton(t("graphics.not_now"), QMessageBox.ButtonRole.RejectRole)
    box.exec()
    clicked = box.clickedButton()
    if clicked not in (enable_restart, enable_later):
        return
    try:
        update_settings({"terminal_graphics_auto_compatibility": True})
    except Exception as exc:
        logging.getLogger("hpc_gui").error("could not save terminal graphics preference: %s", exc)
        QMessageBox.warning(window, t("common.error"), t("graphics.preference_save_failed"))
        return
    if clicked is enable_later:
        return
    try:
        session = getattr(getattr(window, "login", None), "_session", {})
        if session.get("connected"):
            QMessageBox.information(window, t("graphics.restart_required_title"), t("graphics.restart_deferred"))
            return
        command = restart_command()
        window.close()
        if window.isVisible():
            QMessageBox.warning(window, t("common.error"), t("graphics.restart_deferred"))
            return
        subprocess.Popen(command, env=restart_environment(), cwd=os.getcwd())
    except Exception as exc:
        logging.getLogger("hpc_gui").error("graphics compatibility restart failed: %s", exc)
        QMessageBox.warning(window, t("common.error"), t("graphics.restart_failed"))


def _show_main_window(window: MainWindow, available) -> None:
    window.setMinimumSize(320, 240)
    if available is not None:
        window.resize(
            max(1, min(1200, available.width() - 48)),
            max(1, min(800, available.height() - 80)),
        )
    window.showNormal()


def main() -> int:
    _performance_mark("main_entered")
    app = QApplication(sys.argv)
    _configure_application_identity(app)
    _performance_mark("qapplication_created")
    _set_application_icon(app)
    load_saved_language(system_default_language())
    _performance_mark("language_loaded")

    splash = StartupSplash()
    splash.set_status(t("splash.status_preparing"))
    splash.show()
    # Paint the splash before startup checks and widget construction begin.
    app.processEvents()

    # Logging (file-backed, rotating). Must not crash the GUI.
    setup_logging(level=logging.INFO)
    install_crash_logging()
    install_excepthook()
    qInstallMessageHandler(_qt_message_handler)
    logging.getLogger("hpc_gui").info("process started pid=%s", os.getpid())
    logging.getLogger("hpc_gui.graphics").info(
        "terminal graphics policy=%s remembered=%s applied=%s origin=%s qt_platform=%s session=%s",
        GRAPHICS_BOOTSTRAP.mode,
        GRAPHICS_BOOTSTRAP.remembered_auto_compatibility,
        GRAPHICS_BOOTSTRAP.applied_disable_gpu,
        GRAPHICS_BOOTSTRAP.flag_origin,
        os.environ.get("QT_QPA_PLATFORM", ""),
        os.environ.get("XDG_SESSION_TYPE", ""),
    )
    if is_source_run():
        # Development-only interaction telemetry.  Keep a Python reference on
        # QApplication so Qt does not collect the installed event filter.
        app.debug_telemetry = DebugTelemetry(app)  # type: ignore[attr-defined]
        app.installEventFilter(app.debug_telemetry)  # type: ignore[attr-defined]
        logging.getLogger("hpc_gui.debug.telemetry").info(
            "debug telemetry enabled mode=source"
        )
    try:
        log_startup_snapshot()
    except Exception:
        pass

    splash.set_status(t("splash.status_checking"))
    app.processEvents()
    _bootstrap_safety_checks()
    _performance_mark("bootstrap_checks_complete")

    # Slightly darker neutral background for the whole app (without affecting input widgets).
    app.setStyleSheet(
        """
        QMainWindow { background-color: #f0f0f0; }
        QTabWidget::pane { background-color: #f0f0f0; }
        """
    )

    splash.set_status(t("splash.status_loading"))
    app.processEvents()

    w = MainWindow()
    _performance_mark("main_window_created")
    # Crash-safe shutdown: ensure cleanup runs even if window closeEvent is skipped.
    try:
        app.aboutToQuit.connect(w.graceful_shutdown)
    except Exception:
        pass
    # Keep the restored window within Ubuntu's available desktop area.
    screen = app.primaryScreen()
    _show_main_window(w, screen.availableGeometry() if screen is not None else None)
    _performance_mark("main_window_shown")
    app.processEvents()
    splash.finish(w)
    from PySide6.QtCore import QTimer
    graphics_timer = QTimer(w)
    graphics_timer.setInterval(250)
    graphics_timer.timeout.connect(lambda: _offer_graphics_compatibility(w))
    graphics_timer.start()

    # If the previous session crashed, show the crash dialog on startup.
    try:
        crash_flag = read_crash_flag()
        if crash_flag is not None:
            from hpc_gui.ui.dialogs.send_logs_dialog import SendLogsDialog
            from PySide6.QtCore import QTimer

            def _show_crash_dlg():
                try:
                    dlg = SendLogsDialog(
                        w, crash_context=True,
                        crash_summary=crash_flag.get("summary", ""),
                    )
                    dlg.exec()
                except Exception:
                    pass
                finally:
                    clear_crash_flag()

            QTimer.singleShot(500, _show_crash_dlg)
    except Exception:
        pass

    probe = _performance_probe()
    if probe is not None:
        try:
            probe.attach_to_app(app)
        except Exception:
            probe = None

    # First-run welcome / guide (user can disable permanently)
    try:
        if get_ui_pref_bool("show_welcome", True):
            dlg = WelcomeDialog(w)
            dlg.exec()
            if dlg.dont_show_again_checked():
                set_ui_pref_bool("show_welcome", False)
    except Exception:
        pass

    exit_code = app.exec()
    logging.getLogger("hpc_gui").info("graceful shutdown exit_code=%s", exit_code)
    if probe is not None:
        try:
            probe.finish(exit_code)
        except Exception:
            pass
    return exit_code
