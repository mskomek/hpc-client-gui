"""Regression test proving Command Palette does not open Help."""

def test_command_palette_not_wired_to_help():
    import pathlib
    src = pathlib.Path("src/hpc_gui/ui/main_window.py").read_text(encoding="utf-8")
    assert "_act_command_palette" not in src
    assert "F1" in src
    assert "HelpDialog" in src
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
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    try:
        assert w._help_menu is not None
        help_texts = [a.text() for a in w._help_menu.actions() if not a.isSeparator()]
        assert any("Help Center" in t for t in help_texts)
        menu_texts = [a.text() for a in w._menu_menu.actions() if not a.isSeparator()]
        assert not any("Command Palette" in t for t in menu_texts)
        assert w._act_help_center.shortcut().toString() == "F1"
    finally:
        w.deleteLater()
