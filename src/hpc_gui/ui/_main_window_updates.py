"""Main-window update and changelog ownership (Wave M01).

Mixin owning the first-run changelog dialog and the background update
state machine. The changelog storage helpers patched by tests at
``hpc_gui.ui.main_window`` are resolved through the facade at call time;
all other services are imported from their canonical modules.
"""

import threading
import webbrowser

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication, QDialog, QMessageBox, QPushButton, QTextEdit, QVBoxLayout,
)

from hpc_gui import __version__
from hpc_gui.core.i18n import t
from hpc_gui.core.paths import is_frozen_exe
from hpc_gui.core.platform import current_os
from hpc_gui.services import app_updater
from hpc_gui.services.app_updater import (
    AUTOMATIC_INSTALL_STRATEGIES,
    download_and_verify_release,
    get_latest_release,
    is_newer_version,
    launch_update_installer,
)
from . import _main_window_contracts as _contracts
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


class _MainWindowUpdatesMixin:
    def _show_startup_changelog_if_needed(self) -> None:
        try:
            if _contracts.get_last_seen_changelog_version() == __version__:
                return
            text = _contracts.chronological_changelog(_contracts.load_changelog_text())
            if not text:
                _contracts.set_last_seen_changelog_version(__version__)
                return
            self._show_changelog_dialog(text)
            _contracts.set_last_seen_changelog_version(__version__)
        except Exception:
            try:
                _contracts.set_last_seen_changelog_version(__version__)
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
