from __future__ import annotations

from hpc_gui.core.i18n import load_language, t
from hpc_gui.ui.dialogs.plugin_manager_dialog import PluginManagerDialog
from PySide6.QtWidgets import QLabel
import pytest


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_trusted_tool_disclosure_is_localized_and_accurate():
    load_language("en")
    assert "not OS-sandboxed" in t("plugins.trusted_tool_disclosure")
    assert "not OS-sandboxed" in t("plugins.trusted_tool_disclosure_short")
    load_language("tr")
    assert "sandbox" in t("plugins.trusted_tool_disclosure").lower()


def test_trusted_tool_card_and_details_are_disclosed(qapp, monkeypatch):
    dialog = PluginManagerDialog(fetcher=lambda *_: b"{}")
    entry = {
        "id": "org.hpcclient.ansyslint",
        "name": "ANSYS Linter",
        "version": "0.1.0",
        "publisher": "HPC Client GUI",
        "requires_app": ">=1.5.0",
        "capabilities": ["linter-tool"],
        "description": "Offline linter",
    }
    card = dialog._discover_card(entry, {}, set())
    assert any(
        t("plugins.trusted_tool_disclosure_short") in label.text()
        for label in card.findChildren(QLabel)
    )
    messages = []
    monkeypatch.setattr(
        "PySide6.QtWidgets.QMessageBox.information",
        lambda _parent, _title, text: messages.append(text),
    )
    dialog.show_details(entry)
    assert t("plugins.trusted_tool_disclosure") in messages[0]
