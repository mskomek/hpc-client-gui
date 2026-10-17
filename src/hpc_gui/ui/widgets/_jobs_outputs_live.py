from __future__ import annotations

import shlex

import time

from PySide6.QtCore import QTimer

from PySide6.QtGui import QTextCursor

from PySide6.QtWidgets import QTextEdit

from shiboken6 import isValid

from hpc_gui.config.storage import get_jobs_outputs_refresh_interval_seconds, get_lssrv_auto_refresh_enabled, get_sacct_auto_refresh_enabled, get_squeue_auto_refresh_enabled

from hpc_gui.core.i18n import t

from ._jobs_output_text import _LIVE_TAIL_FILE_RETRY_INTERVAL_MS, _LIVE_TAIL_FILE_RETRY_WINDOW_SECONDS, _LIVE_TAIL_INITIAL_RETRY_SECONDS, _LIVE_TAIL_INTERVAL_MS, _LIVE_TAIL_LINE_COUNT, _OUTPUT_MAX_LINES, _bounded_output_text

from ._jobs_output_follower_views import _OutputFollowerWidget



class _JobsOutputsLiveMixin:
        @staticmethod
        def _has_auto_refresh_enabled() -> bool:
            return any((
                get_squeue_auto_refresh_enabled(),
                get_sacct_auto_refresh_enabled(),
                get_lssrv_auto_refresh_enabled(),
            ))
        def apply_refresh_settings(self) -> None:
            # Re-evaluate a changed minimize preference immediately, including
            # while the application is already minimized.
            self.set_application_minimized(self.window().isMinimized())
            for window in (*self._follow_windows, *self._single_file_follow_windows):
                follower = window.centralWidget()
                if isinstance(follower, _OutputFollowerWidget):
                    follower.set_window_minimized(window.isMinimized())
            interval_ms = max(1000, get_jobs_outputs_refresh_interval_seconds() * 1000)
            self._jobs_refresh_timer.setInterval(interval_ms)
            self._apply_live_refresh_interval()
            if (
                self.session
                and self.session.get("connected")
                and self.is_details_polling_visible()
                and self._has_auto_refresh_enabled()
            ):
                self._jobs_refresh_timer.start()
            else:
                self._jobs_refresh_timer.stop()
        def _poll_jobs_and_lssrv(self) -> None:
            if (
                not self.session
                or not self.session.get("connected")
                or not self.is_details_polling_visible()
                or not self._has_auto_refresh_enabled()
            ):
                self._jobs_refresh_timer.stop()
                return
            self.apply_refresh_settings()
            if get_squeue_auto_refresh_enabled():
                self.refresh_jobs()
            if get_sacct_auto_refresh_enabled():
                self.refresh_sacct()
            if get_lssrv_auto_refresh_enabled():
                self.refresh_lssrv()
        def _apply_live_refresh_interval(self) -> None:
            if self._live_timer.interval() != _LIVE_TAIL_INTERVAL_MS:
                self._live_timer.setInterval(_LIVE_TAIL_INTERVAL_MS)
        def _update_tail_pause_button(self) -> None:
            key = "jobs_outputs.tail_resume" if self._tail_paused else "jobs_outputs.tail_pause"
            self.btn_tail_pause.setText(t(key))
        def _toggle_tail_pause(self) -> None:
            self._tail_paused = not self._tail_paused
            self._update_tail_pause_button()
            if not self._tail_paused:
                for widget in (self.txt_out, self.txt_err):
                    self._scroll_to_latest(widget)
            self._sync_polling(immediate=not self._tail_paused)
        def _find_in_output(self, slot: int) -> None:
            search = self.search_out if slot == 0 else self.search_err
            output = self.txt_out if slot == 0 else self.txt_err
            query = search.text()
            if not query:
                return
            if output.find(query):
                return
            cursor = output.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            output.setTextCursor(cursor)
            output.find(query)
        @staticmethod
        def _scroll_to_latest(
            widget: QTextEdit,
            horizontal_position: int | None = None,
        ) -> None:
            if not isValid(widget):
                return
            if horizontal_position is None:
                horizontal_position = widget.horizontalScrollBar().value()
            cursor = widget.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            widget.setTextCursor(cursor)
            widget.ensureCursorVisible()

            def finish_scroll() -> None:
                if not isValid(widget):
                    return
                scrollbar = widget.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
                horizontal_scrollbar = widget.horizontalScrollBar()
                horizontal_scrollbar.setValue(
                    min(horizontal_position, horizontal_scrollbar.maximum())
                )

            finish_scroll()
            QTimer.singleShot(0, finish_scroll)
        @staticmethod
        def _is_scrolled_to_bottom(widget: QTextEdit) -> bool:
            if not isValid(widget):
                return False
            scrollbar = widget.verticalScrollBar()
            return scrollbar.maximum() - scrollbar.value() <= 1
        @staticmethod
        def _set_live_text(
            widget: QTextEdit,
            text: str,
            *,
            follow_latest: bool,
        ) -> None:
            if not isValid(widget):
                return
            scrollbar = widget.verticalScrollBar()
            horizontal_scrollbar = widget.horizontalScrollBar()
            previous_position = scrollbar.value()
            previous_horizontal_position = horizontal_scrollbar.value()
            widget.document().setMaximumBlockCount(_OUTPUT_MAX_LINES + 1)
            widget.setPlainText(_bounded_output_text(text))
            if follow_latest:
                from .jobs_outputs_widget import JobsOutputsWidget

                JobsOutputsWidget._scroll_to_latest(
                    widget,
                    horizontal_position=previous_horizontal_position,
                )
            else:
                scrollbar.setValue(min(previous_position, scrollbar.maximum()))
                horizontal_scrollbar.setValue(
                    min(previous_horizontal_position, horizontal_scrollbar.maximum())
                )
        def _poll_live(self):
            if self._tail_suspended:
                self._live_timer.stop()
                return
            if not self.is_outputs_refresh_visible():
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
            self._apply_live_refresh_interval()
            files = self.session.get("files")
            ssh = self.session.get("ssh")
            if not files:
                self._live_timer.stop()
                return

            paths = (self.active_out, self.active_err)
            if not any(paths):
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
                            if code == 0:
                                results.append((slot, path, out, ""))
                                continue
                            raise RuntimeError(err.strip() or f"exit={code}")
                        text = files.read_text(path)
                        lines = text.splitlines()[-_LIVE_TAIL_LINE_COUNT:]
                        tail = "\n".join(lines) + ("\n" if lines else "")
                        results.append((slot, path, tail, ""))
                    except Exception as exc:
                        results.append((slot, path, "", str(exc)))
                return results

            def success(results) -> None:
                if not isValid(self):
                    return
                if not self.is_outputs_refresh_visible():
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
                    widget = self.txt_out if slot == 0 else self.txt_err
                    follow_latest = (
                        not self._tail_paused
                        and not self._main_window_minimized
                        and self._is_scrolled_to_bottom(widget)
                    )
                    if error:
                        kind_key = (
                            "jobs_outputs.output_kind"
                            if slot == 0
                            else "jobs_outputs.error_kind"
                        )
                        self._set_live_text(
                            widget,
                            t("jobs_outputs.waiting_for_file_unknown").format(
                                kind=t(kind_key),
                                error=error,
                            ),
                            follow_latest=follow_latest,
                        )
                    else:
                        self._set_live_text(
                            widget,
                            text,
                            follow_latest=follow_latest,
                        )

            self._start_async("tail", fetch, success)
        def retranslate_ui(self):
            details_title = f"{t('jobs.title')} / {t('common.details')}"
            files_title = t("jobs_outputs.files_title")
            outputs_title = t("jobs_outputs.outputs_title") if t("jobs_outputs.outputs_title") != "[jobs_outputs.outputs_title]" else "Çıktılar"
            self.section_tabs.setTabText(0, details_title)
            self.section_tabs.setTabText(1, files_title)
            self.section_tabs.setTabText(2, outputs_title)
            self.jobs_box.setTitle(t("jobs.title") if t("jobs.title") != "[jobs.title]" else "İşler")
            self.meta_box.setTitle(t("jobs_outputs.accounting_details"))
            self.lssrv_box.setTitle(t("jobs_outputs.lssrv_title"))
            self.out_group.setTitle(outputs_title)
            self.out_box.setTitle(t("jobs_outputs.output_stdout"))
            self.err_box.setTitle(t("jobs_outputs.output_stderr"))
            self.lbl_script.setText(t("jobs_outputs.no_script") if t("jobs_outputs.no_script") != "[jobs_outputs.no_script]" else "Aktif Slurm Script: (yok)")
            self.btn_refresh.setText(t("jobs.refresh") if t("jobs.refresh") != "[jobs.refresh]" else "Yenile")
            self.btn_cancel.setText(t("jobs.cancel"))
            self.cancel_id.setPlaceholderText(t("jobs.job_id"))
            self.meta_job_id.setPlaceholderText(t("jobs.job_id"))
            self.meta_text.setPlaceholderText(t("jobs_outputs.accounting_placeholder"))
            self.btn_sacct.setText(t("jobs_outputs.refresh_sacct"))
            self.btn_scontrol.setText(t("jobs_outputs.show_job_details"))
            self.btn_lssrv.setText(t("jobs_outputs.lssrv_refresh"))
            self.btn_files_refresh.setText(t("dirs.refresh"))
            self.search_out.setPlaceholderText(t("jobs_outputs.search_placeholder"))
            self.search_err.setPlaceholderText(t("jobs_outputs.search_placeholder"))
            self.btn_search_out.setText(t("jobs_outputs.search_next"))
            self.btn_search_err.setText(t("jobs_outputs.search_next"))
            self._update_tail_pause_button()
