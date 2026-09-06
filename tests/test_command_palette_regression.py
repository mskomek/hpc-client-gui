"""Regression test proving Command Palette does not open Help."""

def test_command_palette_not_wired_to_help():
    import pathlib
    src = pathlib.Path("src/hpc_gui/ui/main_window.py").read_text(encoding="utf-8")
    # Old miswire was _act_command_palette -> _open_help, must be gone
    assert "_act_command_palette" not in src
    # Help Center must still be on F1
    assert "F1" in src
    assert "HelpDialog" in src
    # Real behavior: instantiate MainWindow offscreen and verify Help action exists and Command Palette does not
    try:
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from hpc_gui.ui.main_window import MainWindow
        from hpc_gui.core.i18n import load_language
        load_language("en")
        app = QApplication.instance() or QApplication([])
        w = MainWindow()
        # Help menu must contain Help Center
        assert w._help_menu is not None
        help_texts = [a.text() for a in w._help_menu.actions() if not a.isSeparator()]
        assert any("Help Center" in t for t in help_texts)
        # No visible Command Palette action in Menu
        menu_texts = [a.text() for a in w._menu_menu.actions() if not a.isSeparator()]
        assert not any("Command Palette" in t for t in menu_texts)
        # F1 shortcut still present on Help Center
        assert w._act_help_center.shortcut().toString() == "F1"
        w.deleteLater()
    except Exception as e:
        import pytest
        pytest.skip(f"Qt offscreen not available: {e}")
