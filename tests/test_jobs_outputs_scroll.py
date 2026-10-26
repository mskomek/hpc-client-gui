"""Jobs output scrolling behavior tests."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from hpc_gui.ui.widgets.jobs_outputs_widget import JobsOutputsWidget
from support.jobs_outputs_test_case import JobsOutputsTestCase


class JobsOutputsScrollingTests(JobsOutputsTestCase):
        @pytest.mark.gui
        @pytest.mark.qt
        def test_live_follow_scrolls_to_latest_line(self) -> None:
            JobsOutputsWidget._set_live_text(
                self.editor,
                self._lines(200),
                follow_latest=True,
            )

            self.assertEqual(
                self.editor.textCursor().position(),
                len(self.editor.toPlainText()),
            )
            self.app.processEvents()

            scrollbar = self.editor.verticalScrollBar()
            self.assertEqual(scrollbar.value(), scrollbar.maximum())

        @pytest.mark.gui
        @pytest.mark.qt
        def test_refresh_without_follow_preserves_scroll_position(self) -> None:
            self.editor.setPlainText(self._lines(200))
            self.app.processEvents()
            scrollbar = self.editor.verticalScrollBar()
            scrollbar.setValue(25)

            JobsOutputsWidget._set_live_text(
                self.editor,
                self._lines(220),
                follow_latest=False,
            )
            self.app.processEvents()

            self.assertEqual(scrollbar.value(), 25)
            self.assertLess(scrollbar.value(), scrollbar.maximum())

        @pytest.mark.gui
        @pytest.mark.qt
        def test_refresh_preserves_horizontal_position_when_following_latest(self) -> None:
            long_line = "x" * 240
            self.editor.setPlainText("\n".join(f"{long_line}{index}" for index in range(200)))
            self.app.processEvents()
            vertical_scrollbar = self.editor.verticalScrollBar()
            horizontal_scrollbar = self.editor.horizontalScrollBar()
            vertical_scrollbar.setValue(vertical_scrollbar.maximum())
            horizontal_scrollbar.setValue(40)
            self.assertTrue(JobsOutputsWidget._is_scrolled_to_bottom(self.editor))

            JobsOutputsWidget._set_live_text(
                self.editor,
                "\n".join(f"{long_line}{index}" for index in range(220)),
                follow_latest=True,
            )
            self.app.processEvents()

            self.assertEqual(vertical_scrollbar.value(), vertical_scrollbar.maximum())
            self.assertEqual(horizontal_scrollbar.value(), 40)

        @pytest.mark.gui
        @pytest.mark.qt
        def test_bottom_state_controls_follow_per_refresh(self) -> None:
            self.editor.setPlainText(self._lines(200))
            self.app.processEvents()
            scrollbar = self.editor.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            self.assertTrue(JobsOutputsWidget._is_scrolled_to_bottom(self.editor))

            JobsOutputsWidget._set_live_text(
                self.editor,
                self._lines(220),
                follow_latest=JobsOutputsWidget._is_scrolled_to_bottom(self.editor),
            )
            self.app.processEvents()
            self.assertEqual(scrollbar.value(), scrollbar.maximum())

            scrollbar.setValue(max(0, scrollbar.maximum() - 20))
            self.assertFalse(JobsOutputsWidget._is_scrolled_to_bottom(self.editor))
            previous = scrollbar.value()
            JobsOutputsWidget._set_live_text(
                self.editor,
                self._lines(230),
                follow_latest=JobsOutputsWidget._is_scrolled_to_bottom(self.editor),
            )
            self.app.processEvents()
            self.assertEqual(scrollbar.value(), previous)

        @pytest.mark.gui
        @pytest.mark.qt
        def test_page_navigation_and_end_update_scroll_position(self) -> None:
            self.editor.setPlainText(self._lines(300))
            self.editor.setFocus()
            self.app.processEvents()
            scrollbar = self.editor.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

            QTest.keyClick(self.editor, Qt.Key.Key_PageUp)
            self.app.processEvents()
            self.assertLess(scrollbar.value(), scrollbar.maximum())

            before = scrollbar.value()
            QTest.keyClick(self.editor, Qt.Key.Key_PageDown)
            self.app.processEvents()
            self.assertGreaterEqual(scrollbar.value(), before)

            QTest.keyClick(self.editor, Qt.Key.Key_End)
            self.app.processEvents()
            self.assertEqual(scrollbar.value(), scrollbar.maximum())

        @pytest.mark.gui
        @pytest.mark.qt
        def test_pause_changes_scrolling_without_stopping_refresh_timer(self) -> None:
            widget = JobsOutputsWidget()
            widget.session = {"connected": True}
            widget.active_out = "/tmp/output.log"
            widget.section_tabs.setCurrentWidget(widget.outputs_tab)
            widget._live_timer.start()

            widget._toggle_tail_pause()

            self.assertTrue(widget._tail_paused)
            self.assertTrue(widget._live_timer.isActive())
            self.assertFalse(widget.btn_tail_pause.isVisible())
            widget.shutdown()
            widget.deleteLater()
