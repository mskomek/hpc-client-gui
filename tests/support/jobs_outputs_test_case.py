"""Shared Qt widget lifecycle for Jobs outputs tests."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTextEdit

from hpc_gui.ui.widgets.jobs_outputs_widget import _NavigableTextEdit


class JobsOutputsTestCase(unittest.TestCase):
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
