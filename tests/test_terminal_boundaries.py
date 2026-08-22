import ast
import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


ROOT = Path(__file__).parents[1]


def imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


class TerminalBoundaryTests(unittest.TestCase):
    def test_terminal_bridge_does_not_depend_on_login_widget(self):
        names = imports(ROOT / "src/hpc_gui/services/terminal_bridge.py")
        self.assertFalse(any("login_widget" in name for name in names))

    def test_terminal_header_does_not_own_ssh_or_profile_logic(self):
        names = imports(ROOT / "src/hpc_gui/ui/widgets/terminal_header.py")
        self.assertFalse(any(name.startswith("hpc_gui.ssh") for name in names))
        self.assertFalse(any("config.storage" in name for name in names))

    def test_terminal_header_uses_compact_tool_buttons(self):
        from PySide6.QtWidgets import QApplication, QToolButton
        from hpc_gui.ui.widgets.terminal_header import TerminalHeader

        QApplication.instance() or QApplication([])
        header = TerminalHeader()
        self.addCleanup(header.deleteLater)
        self.assertTrue(all(isinstance(button, QToolButton) for button in (            header.find_button,
            header.clear_button,
            header.font_down_button,
            header.font_up_button,
        )))

    def test_terminal_status_is_plain_single_line_text(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtWidgets import QFrame
        from hpc_gui.ui.widgets.terminal_header import TerminalHeader

        QApplication.instance() or QApplication([])
        header = TerminalHeader()
        self.addCleanup(header.deleteLater)
        self.assertEqual(header.status_label.frameShape(), QFrame.Shape.NoFrame)
        self.assertFalse(header.status_label.wordWrap())


if __name__ == "__main__":
    unittest.main()
