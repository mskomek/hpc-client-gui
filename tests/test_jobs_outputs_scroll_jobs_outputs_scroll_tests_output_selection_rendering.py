from __future__ import annotations
from support.test_jobs_outputs_scroll_shared import (
    JobsOutputsWidget,
    QApplication,
    QCoreApplication,
    QEvent,
    QTextEdit,
    _NavigableTextEdit,
    pytest,
    unittest,
)

class JobsOutputsScrollTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
    def setUp(self) -> None:
        self.editor = _NavigableTextEdit()
        self.editor.setLineWrapMode(QTextEdit.NoWrap)
        self.editor.resize(320, 120)
        self.editor.show()
        self.app.processEvents()
    def tearDown(self) -> None:
        self.editor.close()
        self.editor.deleteLater()
    @staticmethod
    def _lines(count: int) -> str:
        return "\n".join(f"line {index}" for index in range(count))
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
