"""Main-window workspace and session ownership (Wave M01).

Mixin owning tab composition fan-out (session changes, polling sync),
shell/editor routing, script-submission follow, job polling/finish
notices and the simple Help/Settings/Logs/About/Tour openers. The
``get_sbatch_follow_mode`` helper patched by tests at
``hpc_gui.ui.main_window`` is resolved through the facade at call time.
"""

import logging
import shlex
from pathlib import Path

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import QMainWindow, QSystemTrayIcon

from hpc_gui.config.storage import (
    SBATCH_FOLLOW_MODE_NEW_TABS_SPLIT,
    SBATCH_FOLLOW_MODE_OUTPUTS_TAB,
    get_squeue_auto_refresh_enabled,
)
from . import _main_window_contracts as _contracts
from hpc_gui.core.i18n import t
from .async_call import AsyncCall
from .dialogs.help_dialog import HelpDialog
from .dialogs.send_logs_dialog import SendLogsDialog
from .dialogs.settings_dialog import SettingsDialog
from .dialogs.quick_tour import QuickTourOverlay
from .widgets.editor_widget import EditorWidget


class _MainWindowWorkspaceMixin:
    def run_shell_batch_in_terminal(self, script_paths: list[str]) -> None:
        commands = [f"bash {shlex.quote(path)}" for path in script_paths if path]
        if not commands:
            return
        self.tabs.setCurrentWidget(self.login)
        self.login.run_command_text("\n".join(commands))

    def run_shell_in_terminal(self, script_path: str) -> None:
        self.run_shell_batch_in_terminal([script_path])

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

    def start_quick_tour(self):
        try:
            overlay = QuickTourOverlay(self)
            overlay.show()
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
            content = Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
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
            follow_mode = _contracts.get_sbatch_follow_mode()
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
