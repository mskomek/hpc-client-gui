"""Regression test proving Help remains a separate, visible F1 action."""

import pytest


@pytest.mark.gui
@pytest.mark.qt
@pytest.mark.semantic
@pytest.mark.regression
def test_command_palette_not_wired_to_help(monkeypatch):
    try:
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
    except ImportError as e:
        import pytest
        pytest.skip(f"PySide6 unavailable: {e}")
    from hpc_gui.core.i18n import load_language
    from hpc_gui.ui.main_window import MainWindow
    load_language("en")
    _app = QApplication.instance() or QApplication([])
    opened_help = []
    monkeypatch.setattr(MainWindow, "_open_help", lambda self: opened_help.append(self))
    w = MainWindow()
    try:
        menu_actions = [
            action
            for menu_action in w.menuBar().actions()
            if menu_action.menu() is not None
            for action in menu_action.menu().actions()
            if not action.isSeparator()
        ]
        assert not any("Command Palette" in action.text() for action in menu_actions)
        assert w._act_help_center in menu_actions
        assert w._act_help_center.shortcut().toString() == "F1"
        w._act_help_center.trigger()
        assert opened_help == [w]
    finally:
        w.deleteLater()
