"""Jobs output follow-window behavior tests."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMainWindow
from hpc_gui.ui.widgets.jobs_outputs_widget import JobsOutputsWidget
from support.jobs_outputs_test_case import JobsOutputsTestCase


class JobsOutputsFollowWindowTests(JobsOutputsTestCase):
        @pytest.mark.gui
        @pytest.mark.qt
        def test_follow_window_output1_then_assigns_output2(self) -> None:
            widget = JobsOutputsWidget()
            try:
                widget.open_in_output_window(0, "/tmp/stdout.log")
                self.app.processEvents()

                self.assertEqual(len(widget._follow_windows), 1)
                window = widget._follow_windows[0]
                self.assertIsInstance(window, QMainWindow)
                self.assertTrue(window.isWindow())
                self.assertIsNone(window.parentWidget())
                target_id, _label = widget._output_target_choices()[0]
                follower = widget._follow_targets[target_id]
                self.assertEqual(follower.active_out, "/tmp/stdout.log")
                self.assertEqual(follower.active_err, "")
                self.assertTrue(follower.err_box.isVisible())

                widget.open_in_existing_follower(
                    target_id,
                    1,
                    "/tmp/stderr.log",
                )

                self.assertEqual(follower.active_out, "/tmp/stdout.log")
                self.assertEqual(follower.active_err, "/tmp/stderr.log")
                self.assertEqual(follower.path_err.text(), "/tmp/stderr.log")
            finally:
                widget.shutdown()
                widget.deleteLater()
                self.app.processEvents()

        @pytest.mark.gui
        @pytest.mark.qt
        def test_follow_tab_output2_then_assigns_output1_and_is_closable(self) -> None:
            widget = JobsOutputsWidget()
            try:
                self.assertEqual(widget.section_tabs.count(), 3)
                widget.open_in_output_tab(1, "/tmp/stderr.log")
                self.app.processEvents()

                self.assertEqual(widget.section_tabs.count(), 4)
                target_id, _label = widget._output_target_choices()[0]
                follower = widget._follow_targets[target_id]
                self.assertEqual(follower.active_out, "")
                self.assertEqual(follower.active_err, "/tmp/stderr.log")
                self.assertFalse(follower.out_box.isHidden())

                widget.open_in_existing_follower(
                    target_id,
                    0,
                    "/tmp/stdout.log",
                )

                self.assertEqual(follower.active_out, "/tmp/stdout.log")
                self.assertEqual(follower.active_err, "/tmp/stderr.log")
                self.assertEqual(follower.path_out.text(), "/tmp/stdout.log")

                widget._close_follow_tab(0)
                self.assertEqual(widget.section_tabs.count(), 4)
                widget._close_follow_tab(3)
                self.assertEqual(widget.section_tabs.count(), 3)
                self.assertEqual(widget._output_target_choices(), [])
            finally:
                widget.shutdown()
                widget.deleteLater()
                self.app.processEvents()

        @pytest.mark.gui
        @pytest.mark.qt
        def test_main_output_address_enter_switches_follow_target(self) -> None:
            widget = JobsOutputsWidget()
            try:
                self.assertFalse(widget.path_out.isReadOnly())
                self.assertFalse(widget.path_err.isReadOnly())
                widget.path_out.setText("  /tmp/other-output.log  ")

                widget.path_out.returnPressed.emit()

                self.assertEqual(widget.active_out, "/tmp/other-output.log")
                self.assertEqual(widget.path_out.text(), "/tmp/other-output.log")
                self.assertEqual(widget.section_tabs.currentWidget(), widget.outputs_tab)
            finally:
                widget.shutdown()
                widget.deleteLater()
                self.app.processEvents()

        @pytest.mark.gui
        @pytest.mark.qt
        def test_single_file_follow_window_address_accepts_typing_and_enter(self) -> None:
            widget = JobsOutputsWidget()
            try:
                window = widget.open_file_follow_window("/tmp/stdout.log")
                self.assertIsNotNone(window)
                follower = window.centralWidget()
                self.assertFalse(follower.path_out.isReadOnly())
                follower.path_out.setFocus()
                follower.path_out.selectAll()

                QTest.keyClicks(follower.path_out, "/tmp/reassigned.log")
                self.app.processEvents()

                self.assertEqual(follower.path_out.text(), "/tmp/reassigned.log")

                QTest.keyClick(follower.path_out, Qt.Key.Key_Return)
                self.app.processEvents()

                self.assertEqual(follower.active_out, "/tmp/reassigned.log")
                self.assertEqual(follower.path_out.text(), "/tmp/reassigned.log")
                self.assertFalse(follower.err_box.isVisible())
            finally:
                widget.shutdown()
                widget.deleteLater()
                self.app.processEvents()
