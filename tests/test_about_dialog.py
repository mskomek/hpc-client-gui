"""About dialog tests."""

def test_about_shows_version_and_no_network(monkeypatch):
    import os
    from types import SimpleNamespace

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    import hpc_gui.ui.dialogs.about_dialog as about_dialog

    opened_urls = []
    monkeypatch.setattr(
        about_dialog,
        "QDesktopServices",
        SimpleNamespace(openUrl=lambda url: opened_urls.append(url.toString())),
    )
    app = QApplication.instance() or QApplication([])
    dialog = about_dialog.AboutDialog()
    try:
        dialog.show()
        app.processEvents()
        assert dialog.isVisible()
        assert about_dialog.__version__ in dialog._version_label_ref.text()
        assert opened_urls == []

        dialog._repo_btn.click()
        assert opened_urls == ["https://github.com/mskomek/hpc-client-gui"]
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()
