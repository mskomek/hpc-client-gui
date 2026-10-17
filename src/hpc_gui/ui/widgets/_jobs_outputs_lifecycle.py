from __future__ import annotations

import time

from PySide6.QtCore import QThreadPool

from PySide6.QtWidgets import QMessageBox

from shiboken6 import isValid

from hpc_gui.config.storage import get_live_tracking_warning_interval_seconds, get_lssrv_auto_refresh_enabled, get_pause_live_follow_when_minimized_enabled, get_sacct_auto_refresh_enabled, get_squeue_auto_refresh_enabled

from hpc_gui.core.i18n import t

from hpc_gui.config.system_profile import format_remote_path, normalize_system_settings

from hpc_gui.ui.async_call import AsyncCall

from ._jobs_output_text import _LIVE_TAIL_INTERVAL_MS, _LIVE_TAIL_MAX_RETRY_INTERVAL_MS, _LIVE_TAIL_SLOW_INTERVAL_MS

from ._jobs_output_follower_views import _OutputFollowerWidget, _SingleFileFollowerWidget



class _JobsOutputsLifecycleMixin:
        def set_session(self, session):
            self._session_generation += 1
            self._async_busy.clear()
            self.session = session
            self._tracking.set_session(session)
            self._reset_live_tail_idle_state()
            self.jobs_text.setPlainText("")
            self.txt_out.setPlainText("")
            self.txt_err.setPlainText("")
            self.path_out.setText("")
            self.path_err.setText("")
            self.meta_text.setPlainText("")
            self.meta_job_script.clear()
            self.meta_job_workdir.clear()
            self.meta_job_id.setText("")
            self._detail_scheduler_paths = ("", "")
            self.lssrv_text.setPlainText("")
            self.active_script = ""
            self.active_out = ""
            self.active_err = ""
            self._last_sig = [None, None]
            self._tail_paused = False
            self._tail_suspended = False
            self._live_tail_failures = 0
            self._update_tail_pause_button()
            self._live_timer.stop()
            self._jobs_refresh_timer.stop()
            self.apply_refresh_settings()
            for follower in list(self._follow_targets.values()):
                follower.set_session(session)
            for window in list(self._single_file_follow_windows):
                follower = window.centralWidget()
                if isinstance(follower, _SingleFileFollowerWidget):
                    follower.set_session(session)

            if not session or not session.get("connected"):
                return

            cfg = session.get("cfg")
            user = getattr(cfg, "username", "") if cfg else ""
            system = normalize_system_settings(
                getattr(cfg, "system_settings", None) if cfg else None
            )
            scratch_dir = format_remote_path(system["scratch_dir"], user)
            self.scratch_panel.set_session(session)
            self.scratch_panel.title = scratch_dir
            self.scratch_panel.lbl.setText(scratch_dir)
            self.scratch_panel.set_dir(scratch_dir)
            self._sync_polling(immediate=True)
        def set_page_active(self, active: bool) -> None:
            active = bool(active)
            if self._page_active == active:
                return
            self._page_active = active
            self._tracking.set_page_active(active)
            self._sync_polling(immediate=active)
            self.polling_visibility_changed.emit()
        def set_application_minimized(self, minimized: bool) -> None:
            """Pause/resume the main Outputs follower with the app window state."""
            should_pause = bool(
                minimized and get_pause_live_follow_when_minimized_enabled()
            )
            if self._main_window_minimized == should_pause:
                return
            self._main_window_minimized = should_pause
            self._tracking.set_minimized(should_pause)
            if should_pause:
                self._minimize_started_at = time.monotonic()
            elif self._minimize_started_at is not None:
                paused_for = time.monotonic() - self._minimize_started_at
                self._minimize_started_at = None
                self._live_tail_last_change += paused_for
                if self._live_tail_failure_started is not None:
                    self._live_tail_failure_started += paused_for
            self._sync_polling(immediate=not should_pause)
        def is_details_polling_visible(self) -> bool:
            return self._tracking.should_poll_jobs(
                self.section_tabs.currentWidget() is self.details_tab,
                True,
            )
        def is_outputs_polling_visible(self) -> bool:
            self._tracking.set_output_metadata(stdout_path=self.active_out, stderr_path=self.active_err)
            return self._tracking.should_follow_output(
                self.section_tabs.currentWidget() is self.outputs_tab,
            )
        def is_outputs_refresh_visible(self) -> bool:
            return bool(
                self.session
                and self.session.get("connected")
                and self._page_active
                and self.section_tabs.currentWidget() is self.outputs_tab
                and (self.active_out or self.active_err)
            )
        def _on_section_tab_changed(self, _index: int) -> None:
            self._sync_polling(immediate=True)
            self.polling_visibility_changed.emit()
        def _sync_polling(self, *, immediate: bool = False) -> None:
            connected = bool(self.session and self.session.get("connected"))
            if (
                connected
                and self.is_details_polling_visible()
                and self._has_auto_refresh_enabled()
            ):
                self._jobs_refresh_timer.start()
                if immediate:
                    if get_squeue_auto_refresh_enabled():
                        self.refresh_jobs()
                    if get_sacct_auto_refresh_enabled():
                        self.refresh_sacct()
                    if get_lssrv_auto_refresh_enabled():
                        self.refresh_lssrv()
            else:
                self._jobs_refresh_timer.stop()

            should_tail = bool(
                connected
                and self.is_outputs_refresh_visible()
            )
            if should_tail:
                self._apply_live_refresh_interval()
                self._live_timer.start()
                if immediate:
                    self._poll_live()
            else:
                self._live_timer.stop()
        def shutdown(self) -> None:
            """Stop timers / live watchers (best-effort)."""
            try:
                if hasattr(self, "_live_timer") and self._live_timer:
                    self._live_timer.stop()
                if hasattr(self, "_jobs_refresh_timer") and self._jobs_refresh_timer:
                    self._jobs_refresh_timer.stop()
                self._session_generation += 1
                self._async_busy.clear()
                for worker in tuple(self._async_workers):
                    for signal in (worker.signals.finished, worker.signals.failed):
                        try:
                            signal.disconnect()
                        except (RuntimeError, TypeError):
                            pass
                for follower in list(self._follow_tabs):
                    follower.shutdown()
                for window in list(self._follow_windows):
                    follower = window.centralWidget()
                    if isinstance(follower, _OutputFollowerWidget):
                        follower.shutdown()
                    window.close()
                for window in list(self._single_file_follow_windows):
                    follower = window.centralWidget()
                    if isinstance(follower, _SingleFileFollowerWidget):
                        follower.shutdown()
                    window.close()
            except Exception:
                pass
        def _invalidate_async_callbacks(self, *_args) -> None:
            """Make pending worker results stale without touching Qt children."""
            self._session_generation += 1
            self._async_busy.clear()
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
            dialog = QMessageBox(self)
            dialog.setIcon(QMessageBox.Icon.Information)
            dialog.setWindowTitle(t("jobs_outputs.tail_stopped_title"))
            dialog.setText(t("jobs_outputs.tail_stopped_message"))
            dialog.setInformativeText(reason)
            resume = dialog.addButton(t("jobs_outputs.tail_resume"), QMessageBox.ButtonRole.AcceptRole)
            close = dialog.addButton(t("jobs_outputs.tail_close_screen"), QMessageBox.ButtonRole.DestructiveRole)
            dialog.exec()
            clicked = dialog.clickedButton()
            self._tail_alert_visible = False
            if clicked is resume:
                self._tail_suspended = False
                self._live_timer.setInterval(_LIVE_TAIL_SLOW_INTERVAL_MS)
                self._live_timer.start()
                self._poll_live()
            else:
                self._tail_suspended = True
                self._live_timer.stop()
                if clicked is close:
                    self.section_tabs.setCurrentWidget(self.files_tab)
        def _start_async(
            self,
            key: str,
            fn,
            on_success,
            *,
            on_error=None,
        ) -> bool:
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
                if current_token != (key, self._session_generation):
                    return
                on_success(result)

            def failed(current_token, exc) -> None:
                if not isValid(self):
                    return
                self._async_workers.discard(worker)
                if self._async_busy.get(key) == generation:
                    self._async_busy.pop(key, None)
                if current_token != (key, self._session_generation):
                    return
                if on_error is not None:
                    on_error(exc)

            worker.signals.finished.connect(finished)
            worker.signals.failed.connect(failed)
            QThreadPool.globalInstance().start(worker)
            return True
