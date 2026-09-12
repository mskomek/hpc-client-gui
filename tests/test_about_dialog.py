"""About dialog tests."""


import os
import subprocess
import sys
import textwrap
from pathlib import Path


def test_about_shows_version_and_no_network():
    root = Path(__file__).resolve().parents[1]
    code = textwrap.dedent(
        """
        import os
        import socket
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtWidgets import QApplication
        from hpc_gui import __version__
        from hpc_gui.ui.dialogs.about_dialog import AboutDialog

        app = QApplication.instance() or QApplication([])
        opened = []
        def deny_network(*args, **kwargs):
            raise AssertionError("About dialog attempted a network connection")
        socket.create_connection = deny_network
        socket.socket.connect = deny_network
        QDesktopServices.openUrl = staticmethod(lambda url: opened.append(url) or True)
        dialog = AboutDialog()
        assert __version__ in dialog._version_label_ref.text()
        assert dialog._repo_btn.text()
        assert dialog._license_btn.text()
        assert opened == []
        dialog._repo_btn.click()
        assert len(opened) == 1
        assert opened[0].toString() == "https://github.com/mskomek/hpc-client-gui"
        dialog.hide()
        print("about-dialog-behavior=PASS", flush=True)
        os._exit(0)
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=root,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONPATH": str(root / "src")},
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, f"About dialog behavior failed: {result.stdout}\n{result.stderr}"

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
    _app = QApplication.instance() or QApplication([])
    dlg = AboutDialog()
    assert dlg is not None
    assert __version__ in dlg._version_label_ref.text()
    dlg.deleteLater()
