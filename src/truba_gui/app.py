import sys
import os
import logging
from PySide6.QtCore import qInstallMessageHandler
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from pathlib import Path

from truba_gui.core.i18n import load_saved_language, system_default_language
from truba_gui.core.i18n import validate_language_files
from truba_gui.core.logging_setup import setup_logging, install_crash_logging, install_excepthook
from truba_gui.core.debug_support import log_startup_snapshot
from truba_gui.core.debug_telemetry import DebugTelemetry, is_source_run
from truba_gui.ui.main_window import MainWindow
from truba_gui.config.storage import get_ui_pref_bool, set_ui_pref_bool
from truba_gui.ui.dialogs.welcome_dialog import WelcomeDialog
from truba_gui.ui.splash_screen import StartupSplash


def _performance_probe():
    return sys.modules.get("_truba_gui_perf_probe")


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
        Path(__file__).resolve().parents[2] / "build" / "windows" / "hpc-client-gui.ico",
        Path(getattr(sys, "_MEIPASS", "")) / "truba_gui" / "assets" / "hpc-client-gui.ico",
    ]
    for icon_path in candidates:
        if icon_path.is_file():
            app.setWindowIcon(QIcon(str(icon_path)))
            return


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
        from truba_gui.services.process_registry import cleanup_orphans

        # Conservative orphan guard: kills only app-recorded helpers older than 2h.
        cleanup_orphans(aggressive=True)
    except Exception:
        pass

def main() -> int:
    _performance_mark("main_entered")
    app = QApplication(sys.argv)
    _performance_mark("qapplication_created")
    _set_application_icon(app)

    splash = StartupSplash()
    splash.set_status("Preparing workspace...")
    splash.show()
    # Paint the splash before startup checks and widget construction begin.
    app.processEvents()

    # Logging (file-backed, rotating). Must not crash the GUI.
    setup_logging(level=logging.INFO)
    install_crash_logging()
    install_excepthook()
    qInstallMessageHandler(lambda mode, context, message: logging.getLogger("truba_gui.qt").error("Qt message type=%s: %s", mode, message))
    logging.getLogger("truba_gui").info("process started pid=%s", os.getpid())
    if is_source_run():
        # Development-only interaction telemetry.  Keep a Python reference on
        # QApplication so Qt does not collect the installed event filter.
        app.debug_telemetry = DebugTelemetry(app)  # type: ignore[attr-defined]
        app.installEventFilter(app.debug_telemetry)  # type: ignore[attr-defined]
        logging.getLogger("truba_gui.debug.telemetry").info(
            "debug telemetry enabled mode=source"
        )
    try:
        log_startup_snapshot()
    except Exception:
        pass

    splash.set_status("Checking startup environment...")
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

    splash.set_status("Loading interface...")
    app.processEvents()
    load_saved_language(system_default_language())
    _performance_mark("language_loaded")

    w = MainWindow()
    _performance_mark("main_window_created")
    # Crash-safe shutdown: ensure cleanup runs even if window closeEvent is skipped.
    try:
        app.aboutToQuit.connect(w.graceful_shutdown)
    except Exception:
        pass
    w.show()
    _performance_mark("main_window_shown")
    app.processEvents()
    splash.finish(w)

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
    logging.getLogger("truba_gui").info("graceful shutdown exit_code=%s", exit_code)
    if probe is not None:
        try:
            probe.finish(exit_code)
        except Exception:
            pass
    return exit_code
