from __future__ import annotations

import shlex

import time

from PySide6.QtCore import QEvent, QThreadPool, QTimer, Qt

from PySide6.QtGui import QTextCursor

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, QTextEdit, QLineEdit, QLabel, QMessageBox, QMainWindow, QCheckBox

from shiboken6 import isValid

from hpc_gui.config.storage import get_live_tracking_warning_interval_seconds, get_pause_live_follow_when_minimized_enabled

from hpc_gui.core.i18n import t

from hpc_gui.ui.async_call import AsyncCall

from ._jobs_output_text import (
    _ansi_to_html,
    _bounded_output_text,
    _LIVE_TAIL_FILE_RETRY_INTERVAL_MS,
    _LIVE_TAIL_FILE_RETRY_WINDOW_SECONDS,
    _LIVE_TAIL_INITIAL_RETRY_SECONDS,
    _LIVE_TAIL_INTERVAL_MS,
    _LIVE_TAIL_LINE_COUNT,
    _LIVE_TAIL_MAX_RETRY_INTERVAL_MS,
    _LIVE_TAIL_SLOW_INTERVAL_MS,
)



class _NavigableTextEdit(QTextEdit):
    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if (
            event.key() == Qt.Key.Key_End
            and event.modifiers() == Qt.KeyboardModifier.NoModifier
        ):
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)
            self.ensureCursorVisible()
            scrollbar = self.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            event.accept()
            return
        super().keyPressEvent(event)

class _OutputFollowerWidget(QWidget):
    """Lightweight two-slot live follower used by temporary windows and tabs."""

    def __init__(self):
        super().__init__()
        self.session = None
        self._single_slot_mode = False
        self.active_out = ""
        self.active_err = ""
        self._async_workers: set[AsyncCall] = set()
        self._async_busy: dict[str, int] = {}
        self._session_generation = 0
        self._live_tail_failures = 0
        self._live_tail_last_content: tuple[str, ...] | None = None
        self._live_tail_last_change = time.monotonic()
        self._tail_suspended = False
        self._paused_for_minimize = False
        self._minimize_started_at: float | None = None
        self._tail_alert_visible = False
        self._tail_stop_notified = False
        self._live_tail_failure_started: float | None = None

        layout = QVBoxLayout(self)
        self.lbl_script = QLabel(t("jobs_outputs.no_script"))
        layout.addWidget(self.lbl_script)
        self.cb_auto_scroll = QCheckBox(
            t("jobs_outputs.auto_scroll")
            if t("jobs_outputs.auto_scroll") != "[jobs_outputs.auto_scroll]"
            else "Otomatik kaydır"
        )
        self.cb_auto_scroll.setChecked(True)
        self.cb_auto_scroll.toggled.connect(self._on_auto_scroll_toggled)
        layout.addWidget(self.cb_auto_scroll)

        self.out_box = QGroupBox(t("jobs_outputs.output_stdout"))
        out_layout = QVBoxLayout(self.out_box)
        self.path_out = QLineEdit()
        self.path_out.returnPressed.connect(lambda: self._follow_path_from_field(0))
        self.search_out = QLineEdit()
        self.search_out.setPlaceholderText(t("jobs_outputs.search_placeholder"))
        self.btn_search_out = QPushButton(t("jobs_outputs.search_next"))
        self.search_out.returnPressed.connect(lambda: self._find_in_output(0))
        self.btn_search_out.clicked.connect(lambda: self._find_in_output(0))
        out_search = QHBoxLayout()
        out_search.addWidget(self.search_out)
        out_search.addWidget(self.btn_search_out)
        self.txt_out = _NavigableTextEdit()
        self.txt_out.setReadOnly(True)
        out_layout.addWidget(self.path_out)
        out_layout.addLayout(out_search)
        out_layout.addWidget(self.txt_out)

        self.err_box = QGroupBox(t("jobs_outputs.output_stderr"))
        err_layout = QVBoxLayout(self.err_box)
        self.path_err = QLineEdit()
        self.path_err.returnPressed.connect(lambda: self._follow_path_from_field(1))
        self.search_err = QLineEdit()
        self.search_err.setPlaceholderText(t("jobs_outputs.search_placeholder"))
        self.btn_search_err = QPushButton(t("jobs_outputs.search_next"))
        self.search_err.returnPressed.connect(lambda: self._find_in_output(1))
        self.btn_search_err.clicked.connect(lambda: self._find_in_output(1))
        err_search = QHBoxLayout()
        err_search.addWidget(self.search_err)
        err_search.addWidget(self.btn_search_err)
        self.txt_err = _NavigableTextEdit()
        self.txt_err.setReadOnly(True)
        err_layout.addWidget(self.path_err)
        err_layout.addLayout(err_search)
        err_layout.addWidget(self.txt_err)

        layout.addWidget(self.out_box)
        layout.addWidget(self.err_box)
        from .jobs_outputs_widget import JobsOutputsWidget

        JobsOutputsWidget._apply_terminal_output_style(self.txt_out)
        JobsOutputsWidget._apply_terminal_output_style(self.txt_err)

        self._live_timer = QTimer(self)
        self._live_timer.setInterval(_LIVE_TAIL_INTERVAL_MS)
        self._live_timer.timeout.connect(self._poll_live)
        # A top-level follower can be deleted when its window closes while a
        # tail request is still running.  Invalidate its callback token before
        # that request is delivered back to the GUI thread.
        self.destroyed.connect(self._invalidate_async_callbacks)

    def _invalidate_async_callbacks(self, *_args) -> None:
        self._session_generation += 1
        self._async_busy.clear()

    def _on_auto_scroll_toggled(self, enabled: bool) -> None:
        """Immediately catch up when automatic scrolling is re-enabled."""
        if enabled:
            for output in (self.txt_out, self.txt_err):
                from .jobs_outputs_widget import JobsOutputsWidget

                JobsOutputsWidget._scroll_to_latest(output)

    def _record_live_tail_result(self, had_error: bool) -> None:
        """Back off missing/unreadable output files without stopping follow."""
        if had_error:
            self._live_tail_failures += 1
            interval = min(
                _LIVE_TAIL_INTERVAL_MS * (2 ** self._live_tail_failures),
                _LIVE_TAIL_MAX_RETRY_INTERVAL_MS,
            )
        else:
            self._live_tail_failures = 0
            interval = _LIVE_TAIL_INTERVAL_MS
        if self._live_timer.interval() != interval:
            self._live_timer.setInterval(interval)

    def _reset_live_tail_idle_state(self) -> None:
        self._live_tail_last_content = None
        self._live_tail_last_change = time.monotonic()
        self._tail_alert_visible = False
        self._tail_stop_notified = False
        self._live_tail_failure_started = None
        self._live_tail_failure_started = None

    def _observe_live_tail_content(self, results) -> None:
        content = tuple(text for _, _, text, error in results if not error)
        if content != self._live_tail_last_content:
            self._live_tail_last_content = content
            self._live_tail_last_change = time.monotonic()
            self._tail_stop_notified = False
            if self._live_timer.interval() == _LIVE_TAIL_SLOW_INTERVAL_MS:
                self._live_timer.setInterval(_LIVE_TAIL_INTERVAL_MS)
            return
        warning_seconds = get_live_tracking_warning_interval_seconds()
        if (
            warning_seconds > 0
            and not self._tail_stop_notified
            and time.monotonic() - self._live_tail_last_change >= warning_seconds
        ):
            self._live_timer.setInterval(_LIVE_TAIL_SLOW_INTERVAL_MS)
            self._show_tracking_stopped_dialog(f"Çıktı {warning_seconds} saniyedir değişmedi.")

    def _show_tracking_stopped_dialog(self, reason: str) -> None:
        if self._tail_alert_visible or self._tail_suspended or not isValid(self):
            return
        self._tail_alert_visible = True
        self._tail_stop_notified = True
        # QMessageBox.exec() runs a nested event loop.  Stop polling before it
        # starts so neither live following nor its idle/retry countdowns keep
        # progressing while the user decides what to do.
        self._live_timer.stop()
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Information)
        dialog.setWindowTitle(t("jobs_outputs.tail_stopped_title"))
        dialog.setText(t("jobs_outputs.tail_stopped_message"))
        dialog.setInformativeText(reason)
        resume = dialog.addButton(t("jobs_outputs.tail_resume"), QMessageBox.ButtonRole.AcceptRole)
        close = dialog.addButton(t("jobs_outputs.tail_close_window"), QMessageBox.ButtonRole.DestructiveRole)
        dialog.exec()
        clicked = dialog.clickedButton()
        self._tail_alert_visible = False
        if clicked is resume:
            self._tail_suspended = False
            self._reset_live_tail_idle_state()
            self._live_timer.setInterval(_LIVE_TAIL_SLOW_INTERVAL_MS)
            self._live_timer.start()
            self._poll_live()
        elif clicked is close:
            self.window().close()
        else:
            self._tail_suspended = True
            self._live_timer.stop()

    def set_session(self, session) -> None:
        self._session_generation += 1
        self._async_busy.clear()
        self.session = session
        self._reset_live_tail_idle_state()
        if (
            not self._paused_for_minimize
            and session
            and session.get("connected")
            and (self.active_out or self.active_err)
        ):
            self._live_timer.start()
            self._poll_live()
        else:
            self._live_timer.stop()

    def set_window_minimized(self, minimized: bool) -> None:
        """Pause this follower while its top-level window is minimized."""
        pause_enabled = get_pause_live_follow_when_minimized_enabled()
        self._paused_for_minimize = bool(minimized and pause_enabled)
        if self._paused_for_minimize:
            if self._minimize_started_at is None:
                self._minimize_started_at = time.monotonic()
            if self.session and self.session.get("connected") and (self.active_out or self.active_err):
                self._live_timer.start()
            return
        if self._minimize_started_at is not None:
            paused_for = time.monotonic() - self._minimize_started_at
            self._minimize_started_at = None
            self._live_tail_last_change += paused_for
            if self._live_tail_failure_started is not None:
                self._live_tail_failure_started += paused_for
        if (
            self.session
            and self.session.get("connected")
            and (self.active_out or self.active_err)
            and not self._tail_suspended
        ):
            self._live_timer.start()
            self._poll_live()

    def shutdown(self) -> None:
        self._live_timer.stop()
        self._invalidate_async_callbacks()
        for worker in tuple(self._async_workers):
            for signal in (worker.signals.finished, worker.signals.failed):
                try:
                    signal.disconnect()
                except (RuntimeError, TypeError):
                    pass

    def open_in_output_slot(self, slot: int, remote_path: str) -> None:
        if not remote_path or slot not in (0, 1):
            return
        self._tail_suspended = False
        self._reset_live_tail_idle_state()
        if slot == 0:
            self.active_out = remote_path
            self.path_out.setText(remote_path)
            self.txt_out.clear()
        else:
            self.active_err = remote_path
            self.path_err.setText(remote_path)
            self.txt_err.clear()
        # A follower opened with one slot must keep the empty counterpart
        # available for later assignment from the Files context menu.
        self.out_box.show()
        if not self._single_slot_mode:
            self.err_box.show()
        if (
            not self._paused_for_minimize
            and self.session
            and self.session.get("connected")
        ):
            self._live_timer.start()
            self._poll_live()

    def _follow_path_from_field(self, slot: int) -> None:
        field = self.path_out if slot == 0 else self.path_err
        remote_path = field.text().strip()
        if not remote_path:
            field.setText(self.active_out if slot == 0 else self.active_err)
            return
        self.open_in_output_slot(slot, remote_path)

    def _find_in_output(self, slot: int) -> None:
        search = self.search_out if slot == 0 else self.search_err
        output = self.txt_out if slot == 0 else self.txt_err
        query = search.text()
        if not query or output.find(query):
            return
        cursor = output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        output.setTextCursor(cursor)
        output.find(query)

    def _start_async(self, key: str, fn, on_success) -> bool:
        if key in self._async_busy:
            return False
        generation = self._session_generation
        token = (key, generation)
        worker = AsyncCall(token, fn)
        self._async_busy[key] = generation
        self._async_workers.add(worker)

        def finished(current_token, result) -> None:
            if not isValid(self):
                return
            self._async_workers.discard(worker)
            if self._async_busy.get(key) == generation:
                self._async_busy.pop(key, None)
            if current_token == (key, self._session_generation):
                on_success(result)

        def failed(_current_token, _exc) -> None:
            if not isValid(self):
                return
            self._async_workers.discard(worker)
            if self._async_busy.get(key) == generation:
                self._async_busy.pop(key, None)

        worker.signals.finished.connect(finished)
        worker.signals.failed.connect(failed)
        QThreadPool.globalInstance().start(worker)
        return True

    def _poll_live(self) -> None:
        if self._tail_suspended:
            self._live_timer.stop()
            return
        if not self.session or not self.session.get("connected"):
            if self._live_tail_failure_started is None:
                self._live_tail_failure_started = time.monotonic()
            if time.monotonic() - self._live_tail_failure_started < _LIVE_TAIL_INITIAL_RETRY_SECONDS:
                self._live_timer.setInterval(_LIVE_TAIL_INTERVAL_MS)
                self._live_timer.start()
                return
            self._live_timer.stop()
            self._show_tracking_stopped_dialog(t("jobs_outputs.tracking_stopped_disconnected"))
            return
        self._live_tail_failure_started = None
        files = self.session.get("files")
        ssh = self.session.get("ssh")
        paths = (self.active_out, self.active_err)
        if not files or not any(paths):
            self._live_timer.stop()
            return

        def fetch() -> list[tuple[int, str, str, str]]:
            results = []
            for slot, path in enumerate(paths):
                if not path:
                    continue
                try:
                    if ssh:
                        code, out, err = ssh.run(
                            f"tail -n {_LIVE_TAIL_LINE_COUNT} -- {shlex.quote(path)}",
                            log_output=False,
                        )
                        if code != 0:
                            raise RuntimeError(err.strip() or f"exit={code}")
                        text = out
                    else:
                        all_text = files.read_text(path)
                        lines = all_text.splitlines()[-_LIVE_TAIL_LINE_COUNT:]
                        text = "\n".join(lines) + ("\n" if lines else "")
                    results.append((slot, path, text, ""))
                except Exception as exc:
                    results.append((slot, path, "", str(exc)))
            return results

        def success(results) -> None:
            if not isValid(self):
                return
            had_error = any(error for _, _, _, error in results)
            if had_error:
                now = time.monotonic()
                if self._live_tail_failure_started is None:
                    self._live_tail_failure_started = now
                elapsed = now - self._live_tail_failure_started
                if elapsed < _LIVE_TAIL_INITIAL_RETRY_SECONDS:
                    self._live_timer.setInterval(_LIVE_TAIL_INTERVAL_MS)
                elif elapsed < _LIVE_TAIL_INITIAL_RETRY_SECONDS + _LIVE_TAIL_FILE_RETRY_WINDOW_SECONDS:
                    self._live_timer.setInterval(_LIVE_TAIL_FILE_RETRY_INTERVAL_MS)
                else:
                    self._live_timer.stop()
                    self._show_tracking_stopped_dialog("Çıktı dosyasına 5 dakikadır erişilemiyor.")
            else:
                self._live_tail_failure_started = None
                self._record_live_tail_result(False)
                self._observe_live_tail_content(results)
            for slot, path, text, error in results:
                current_path = self.active_out if slot == 0 else self.active_err
                if path != current_path:
                    continue
                output = self.txt_out if slot == 0 else self.txt_err
                follow_latest = self.cb_auto_scroll.isChecked() and not self._paused_for_minimize
                if error:
                    kind_key = (
                        "jobs_outputs.output_kind"
                        if slot == 0
                        else "jobs_outputs.error_kind"
                    )
                    text = t("jobs_outputs.waiting_for_file_unknown").format(
                        kind=t(kind_key),
                        error=error,
                    )
                from .jobs_outputs_widget import JobsOutputsWidget

                JobsOutputsWidget._set_live_text(
                    output,
                    text,
                    follow_latest=follow_latest,
                )

        self._start_async("tail", fetch, success)

class _SingleFileFollowerWidget(_OutputFollowerWidget):
    """Dedicated one-file follower used by the generic new-window action."""

    def __init__(self, remote_path: str):
        super().__init__()
        self._single_slot_mode = True
        # This is the address bar shown in the standalone "Follow: file"
        # window. Keep its editable contract explicit even if the shared
        # two-slot follower changes later.
        self.path_out.setReadOnly(False)
        self.open_in_output_slot(0, remote_path)
        self.err_box.hide()
        self.out_box.setTitle(remote_path.rstrip("/").rsplit("/", 1)[-1] or remote_path)

class _FollowerWindow(QMainWindow):
    """Top-level follower window that propagates minimize/restore state."""

    def changeEvent(self, event) -> None:  # type: ignore[override]
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            follower = self.centralWidget()
            if isinstance(follower, _OutputFollowerWidget):
                follower.set_window_minimized(self.isMinimized())
