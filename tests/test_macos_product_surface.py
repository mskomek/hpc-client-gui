from __future__ import annotations

from unittest import mock


def test_application_identity_uses_product_name():
    from hpc_gui.app import _configure_application_identity

    app = mock.Mock()
    _configure_application_identity(app)

    app.setApplicationName.assert_called_once_with("HPC Client GUI")
    app.setApplicationDisplayName.assert_called_once_with("HPC Client GUI")


def test_macos_hides_vcxsrv_exit_setting(monkeypatch):
    from PySide6.QtWidgets import QApplication
    from hpc_gui.ui.dialogs import settings_dialog

    QApplication.instance() or QApplication([])
    monkeypatch.setattr(settings_dialog, "current_os", lambda: "macos")
    dialog = settings_dialog.SettingsDialog()
    try:
        assert dialog.cb_close_vcxsrv_on_exit.isHidden()
    finally:
        dialog.deleteLater()
