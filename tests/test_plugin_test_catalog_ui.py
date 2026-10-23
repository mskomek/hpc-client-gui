"""Plugin Manager shows the TEST CATALOG badge only while the test override is configured."""

from __future__ import annotations

import pytest

from plugin_test_catalog_fixture import enable_test_catalog
from hpc_gui.core.i18n import load_language
from hpc_gui.plugins.test_catalog import TEST_CATALOG_ENV, TEST_MODE_ENV


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    load_language("en")
    yield app
    load_language("en")


def _badge_labels(dialog) -> list[str]:
    from PySide6.QtWidgets import QLabel

    return [label.text() for label in dialog.findChildren(QLabel) if "TEST CATALOG" in label.text()]


def test_badge_absent_by_default_and_present_in_test_mode(qapp, monkeypatch, tmp_path):
    from hpc_gui.ui.dialogs.plugin_manager_dialog import PluginManagerDialog

    monkeypatch.delenv(TEST_MODE_ENV, raising=False)
    monkeypatch.delenv(TEST_CATALOG_ENV, raising=False)
    plain = PluginManagerDialog(fetcher=lambda url, limit: b"{}")
    try:
        assert "TEST CATALOG" not in plain.windowTitle()
        assert _badge_labels(plain) == []
    finally:
        plain.close()

    enable_test_catalog(monkeypatch, tmp_path)
    marked = PluginManagerDialog(fetcher=lambda url, limit: b"{}")
    try:
        assert marked.windowTitle() == "Plugin Manager — TEST CATALOG"
        assert _badge_labels(marked) == ["Plugin Manager — TEST CATALOG"]
    finally:
        marked.close()
