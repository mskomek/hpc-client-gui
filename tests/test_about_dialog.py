"""About dialog tests."""

def test_about_shows_version_and_no_network():
    import pathlib
    src = pathlib.Path("src/hpc_gui/ui/dialogs/about_dialog.py").read_text(encoding="utf-8")
    assert "__version__" in src
    assert "is_frozen_exe" in src or "frozen" in src
    assert "https://github.com/mskomek/hpc-client-gui" in src
    # Must not require network to instantiate (no requests, no url fetch at init)
    assert "requests" not in src.lower()
    assert "urllib.request.urlopen" not in src

def test_about_instantiates_offscreen():
    try:
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
    except ImportError as e:
        import pytest
        pytest.skip(f"PySide6 unavailable: {e}")
    from hpc_gui.ui.dialogs.about_dialog import AboutDialog
    from hpc_gui import __version__
    app = QApplication.instance() or QApplication([])
    dlg = AboutDialog()
    assert dlg is not None
    assert __version__ in dlg._version_label_ref.text()
    dlg.deleteLater()
