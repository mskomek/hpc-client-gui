"""Jobs output polling behavior tests."""

from __future__ import annotations

import pytest
from unittest.mock import patch
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QMainWindow
from hpc_gui.ui.widgets.jobs_outputs_widget import (
    JobsOutputsWidget,
    _NavigableTextEdit,
    _OutputFollowerWidget,
)
from support.jobs_outputs_test_case import JobsOutputsTestCase


class JobsOutputsPollingTests(JobsOutputsTestCase):
        @staticmethod
        def _run_async_immediately(_key, fn, on_success, **_kwargs) -> bool:
            on_success(fn())
            return True

        def _assert_fake_tail_window_stream(
            self,
            follower,
            paths: tuple[str, ...],
        ) -> None:
            class FakeFiles:
                content: dict[str, str] = {}

                @classmethod
                def read_text(cls, path: str) -> str:
                    return cls.content[path]

            def make_lines(start: int, stop: int) -> str:
                return "\n".join(
                    f"{'x' * 240} line {index}"
                    for index in range(start, stop)
                )

            FakeFiles.content = {path: make_lines(0, 220) for path in paths}
            follower._start_async = self._run_async_immediately
            follower.set_session({"connected": True, "files": FakeFiles(), "ssh": None})
            self.app.processEvents()

            scrollbars = []
            for path in paths:
                output = follower.txt_out if path == follower.active_out else follower.txt_err
                vertical = output.verticalScrollBar()
                horizontal = output.horizontalScrollBar()
                vertical.setValue(vertical.maximum())
                horizontal.setValue(35)
                scrollbars.append((path, output, vertical, horizontal))

            for path in paths:
                FakeFiles.content[path] = make_lines(0, 221)
            follower._poll_live()
            self.app.processEvents()

            for path, _output, vertical, horizontal in scrollbars:
                self.assertEqual(vertical.value(), vertical.maximum(), path)
                self.assertEqual(horizontal.value(), 35, path)

            previous_positions = {}
            follower.cb_auto_scroll.setChecked(False)
            for path, _output, vertical, _horizontal in scrollbars:
                vertical.setValue(max(0, vertical.maximum() - 20))
                previous_positions[path] = vertical.value()

            for path in paths:
                FakeFiles.content[path] = make_lines(0, 240)
            follower._poll_live()
            self.app.processEvents()

            for path, _output, vertical, horizontal in scrollbars:
                self.assertEqual(vertical.value(), previous_positions[path], path)
                self.assertEqual(horizontal.value(), 35, path)

        @pytest.mark.gui
        @pytest.mark.qt
        def test_all_follow_windows_preserve_fake_tail_scroll_positions(self) -> None:
            cases = (
                ("output1", lambda widget: widget.open_in_output_window(0, "/tmp/out.log"), ("/tmp/out.log",)),
                ("output2", lambda widget: widget.open_in_output_window(1, "/tmp/err.log"), ("/tmp/err.log",)),
                (
                    "combined",
                    lambda widget: widget.open_output_pair_window("/tmp/out.log", "/tmp/err.log"),
                    ("/tmp/out.log", "/tmp/err.log"),
                ),
                (
                    "single",
                    lambda widget: widget.open_file_follow_window("/tmp/out.log"),
                    ("/tmp/out.log",),
                ),
            )

            for name, open_window, paths in cases:
                with self.subTest(window=name):
                    widget = JobsOutputsWidget()
                    try:
                        with patch(
                            "hpc_gui.ui.widgets.jobs_outputs_widget."
                            "get_follow_window_open_minimized_enabled",
                            return_value=False,
                        ):
                            result = open_window(widget)
                        window = result or widget._follow_windows[-1]
                        self.assertIsInstance(window, QMainWindow)
                        self.assertTrue(window.isWindow())
                        self._assert_fake_tail_window_stream(
                            window.centralWidget(),
                            paths,
                        )
                    finally:
                        widget.shutdown()
                        widget.deleteLater()
                        self.app.processEvents()

        @pytest.mark.gui
        @pytest.mark.qt
        def test_ssh_poll_requests_last_200_lines_for_both_outputs(self) -> None:
            class FakeSSH:
                def __init__(self) -> None:
                    self.commands = []

                def run(self, command, log_output=False):
                    self.commands.append((command, log_output))
                    return 0, f"content for {command}", ""

            ssh = FakeSSH()
            widget = JobsOutputsWidget()
            widget.section_tabs.setCurrentWidget(widget.outputs_tab)
            widget.session = {"connected": True, "files": object(), "ssh": ssh}
            widget.active_out = "/tmp/output file.log"
            widget.active_err = "/tmp/error file.log"
            widget._start_async = self._run_async_immediately

            widget._poll_live()
            self.app.processEvents()

            self.assertEqual(len(ssh.commands), 2)
            self.assertTrue(all("tail -n 200 --" in command for command, _ in ssh.commands))
            self.assertTrue(all(log_output is False for _, log_output in ssh.commands))
            self.assertIn("content for", widget.txt_out.toPlainText())
            self.assertIn("content for", widget.txt_err.toPlainText())
            widget.shutdown()
            widget.deleteLater()

        @pytest.mark.gui
        @pytest.mark.qt
        def test_file_fallback_displays_only_last_200_lines(self) -> None:
            class FakeFiles:
                @staticmethod
                def read_text(_path):
                    return "\n".join(f"line {index}" for index in range(250))

            widget = JobsOutputsWidget()
            widget.section_tabs.setCurrentWidget(widget.outputs_tab)
            widget.session = {"connected": True, "files": FakeFiles()}
            widget.active_out = "/tmp/output.log"
            widget._start_async = self._run_async_immediately

            widget._poll_live()
            self.app.processEvents()

            lines = widget.txt_out.toPlainText().splitlines()
            self.assertEqual(len(lines), 200)
            self.assertEqual(lines[0], "line 50")
            self.assertNotIn("line 49", lines)
            self.assertEqual(lines[-1], "line 249")
            widget.shutdown()
            widget.deleteLater()

        @pytest.mark.gui
        @pytest.mark.qt
        def test_minimized_main_outputs_page_pauses_and_restores_live_follow(self) -> None:
            widget = JobsOutputsWidget()
            widget.session = {"connected": True, "files": object()}
            widget._tracking.set_session(widget.session)
            widget.active_out = "/tmp/output.log"
            widget.section_tabs.setCurrentWidget(widget.outputs_tab)
            widget._start_async = lambda *_args, **_kwargs: True

            with patch(
                "hpc_gui.ui.widgets.jobs_outputs_widget."
                "get_pause_live_follow_when_minimized_enabled",
                return_value=True,
            ):
                widget.set_application_minimized(True)
                self.assertTrue(widget._live_timer.isActive())
                self.assertFalse(widget.is_outputs_polling_visible())

                widget.set_application_minimized(False)
                self.assertTrue(widget._live_timer.isActive())
                self.assertTrue(widget.is_outputs_polling_visible())

            widget.shutdown()
            widget.deleteLater()

        @pytest.mark.gui
        @pytest.mark.qt
        def test_minimized_follower_pauses_and_restores_live_follow(self) -> None:
            follower = _OutputFollowerWidget()
            follower.session = {"connected": True, "files": object()}
            follower.active_out = "/tmp/output.log"
            follower._start_async = lambda *_args, **_kwargs: True
            follower._live_timer.start()

            with patch(
                "hpc_gui.ui.widgets.jobs_outputs_widget."
                "get_pause_live_follow_when_minimized_enabled",
                return_value=True,
            ):
                follower.set_window_minimized(True)
                self.assertTrue(follower._live_timer.isActive())
                self.assertTrue(follower._paused_for_minimize)

                follower.set_window_minimized(False)
                self.assertTrue(follower._live_timer.isActive())

            follower.shutdown()
            follower.deleteLater()

        @pytest.mark.gui
        @pytest.mark.qt
        def test_minimized_follower_does_not_advance_idle_or_retry_countdowns(self) -> None:
            follower = _OutputFollowerWidget()
            follower.session = {"connected": True, "files": object()}
            follower.active_out = "/tmp/output.log"
            follower._start_async = lambda *_args, **_kwargs: True
            follower._live_tail_last_change = 10.0
            follower._live_tail_failure_started = 20.0
            follower._tail_suspended = True

            with (
                patch(
                    "hpc_gui.ui.widgets.jobs_outputs_widget."
                    "get_pause_live_follow_when_minimized_enabled",
                    return_value=True,
                ),
                patch(
                    "hpc_gui.ui.widgets.jobs_outputs_widget.time.monotonic",
                    side_effect=(100.0, 160.0),
                ),
            ):
                follower.set_window_minimized(True)
                follower.set_window_minimized(False)

            self.assertEqual(follower._live_tail_last_change, 70.0)
            self.assertEqual(follower._live_tail_failure_started, 80.0)
            follower.shutdown()
            follower.deleteLater()

        @pytest.mark.gui
        @pytest.mark.qt
        def test_minimized_main_follower_does_not_advance_idle_or_retry_countdowns(self) -> None:
            widget = JobsOutputsWidget()
            widget._live_tail_last_change = 10.0
            widget._live_tail_failure_started = 20.0

            with (
                patch(
                    "hpc_gui.ui.widgets.jobs_outputs_widget."
                    "get_pause_live_follow_when_minimized_enabled",
                    return_value=True,
                ),
                patch(
                    "hpc_gui.ui.widgets.jobs_outputs_widget.time.monotonic",
                    side_effect=(100.0, 160.0),
                ),
            ):
                widget.set_application_minimized(True)
                widget.set_application_minimized(False)

            self.assertEqual(widget._live_tail_last_change, 70.0)
            self.assertEqual(widget._live_tail_failure_started, 80.0)
            widget.shutdown()
            widget.deleteLater()

        @pytest.mark.gui
        @pytest.mark.qt
        def test_reset_live_tail_state_clears_previous_connection_countdown(self) -> None:
            widget = JobsOutputsWidget()
            widget._live_tail_failure_started = 123.0

            widget._reset_live_tail_idle_state()

            self.assertIsNone(widget._live_tail_failure_started)
            widget.shutdown()
            widget.deleteLater()

        @pytest.mark.gui
        @pytest.mark.qt
        def test_missing_live_output_uses_backoff_then_resets_after_success(self) -> None:
            class FakeSSH:
                result = (1, "", "tail: cannot open file")

                def run(self, _command, log_output=False):
                    if log_output:
                        raise AssertionError("live-tail logging must stay disabled")
                    return self.result

            ssh = FakeSSH()
            widget = JobsOutputsWidget()
            widget.section_tabs.setCurrentWidget(widget.outputs_tab)
            widget.session = {"connected": True, "files": object(), "ssh": ssh}
            widget.active_out = "/tmp/not-created-yet.log"
            widget._start_async = self._run_async_immediately
            widget._show_tracking_stopped_dialog = lambda _reason: None

            widget._poll_live()
            self.assertEqual(widget._live_timer.interval(), 1_000)
            self.assertTrue(widget.txt_out.toPlainText())

            widget._poll_live()
            self.assertEqual(widget._live_timer.interval(), 1_000)

            ssh.result = (0, "file is ready\n", "")
            widget._poll_live()
            self.assertEqual(widget._live_timer.interval(), 1_000)
            self.assertEqual(widget.txt_out.toPlainText(), "file is ready\n")
            widget.shutdown()
            widget.deleteLater()

        @pytest.mark.gui
        @pytest.mark.qt
        def test_live_text_helpers_ignore_deleted_editor(self) -> None:
            editor = _NavigableTextEdit()
            editor.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

            self.assertFalse(JobsOutputsWidget._is_scrolled_to_bottom(editor))
            JobsOutputsWidget._set_live_text(
                editor,
                "late worker result",
                follow_latest=True,
            )
