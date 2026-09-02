import os
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath("src"))

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QMessageBox

from hpc_gui.ui.widgets.editor_widget import EditorWidget


class EditorShortcutSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        self.editor.deleteLater()
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def test_dirty_close_cancel_keeps_document(self):
        self.editor = EditorWidget()
        self.editor.open_file("/remote/dirty.txt", "before")
        self.editor.text.setPlainText("after")
        with patch.object(QMessageBox, "exec", return_value=None):
            self.editor.close_active_tab()
        self.assertEqual(self.editor.document_tabs.count(), 1)
        self.assertTrue(self.editor.document_tabs.tabText(0).endswith(" *"))

    def test_execute_local_shell_saves_and_requests_terminal(self):
        self.editor = EditorWidget()
        self.editor.open_file("C:/work/run.sh", "echo old", is_local=True)
        self.editor.text.setPlainText("echo new")
        requested = []
        self.editor.run_in_terminal_requested.connect(requested.append)
        with patch("hpc_gui.ui.widgets.editor_widget.Path.write_text"):
            self.editor.save_path(run_in_terminal=True)
        self.assertEqual(requested, ["C:/work/run.sh"])
        self.assertFalse(self.editor._is_document_modified(self.editor._current_document()))


if __name__ == "__main__":
    unittest.main()
