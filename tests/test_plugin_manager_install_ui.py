"""Plugin Manager install, update, removal, and search actions."""

from __future__ import annotations

import json
import unittest.mock as mock
from types import SimpleNamespace

import pytest

pytest_plugins = ("support.plugin_manager_ui_fixtures",)

from hpc_gui.core.i18n import t
from hpc_gui.ui.dialogs.plugin_manager_dialog import PluginManagerDialog
from support.plugin_manager_ui import (
    VALID_REGISTRY,
    apply_registry,
    registry_fetcher,
)

@pytest.mark.gui
def test_successful_install_updates_state_and_emits_signal(qapp, frozen_thread_pool):
    dialog = PluginManagerDialog(fetcher=registry_fetcher())
    emitted = []
    summaries = []
    dialog.plugins_changed.connect(lambda: emitted.append(True))
    entry = VALID_REGISTRY["plugins"][0]

    def fake_install(registry_entry, **kwargs):
        return SimpleNamespace(installed=SimpleNamespace(manifest=SimpleNamespace(id=entry["id"])), activated=True)

    class FakeBox:
        Warning = 3

        @staticmethod
        def information(*args, **kwargs):
            summaries.append(args)

        @staticmethod
        def warning(*args, **kwargs):
            pass

    with mock.patch(
        "hpc_gui.plugins.loader.read_active_versions",
        return_value={entry["id"]: entry["version"]},
    ), mock.patch(
        "hpc_gui.plugins.state.read_active_versions", return_value={}
    ), mock.patch(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.read_active_versions",
        return_value={},
    ), mock.patch(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.load_installed_plugins"
    ) as loader, mock.patch(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.install_plugin_from_registry",
        side_effect=fake_install,
    ), mock.patch(
        "PySide6.QtWidgets.QMessageBox", FakeBox
    ):
        loader.return_value = SimpleNamespace(plugins=[])
        dialog.refresh_registry()
        # Run the worker synchronously for deterministic tests; run() emits
        # its own finished/failed signals.
        worker = dialog._refresh_worker
        assert worker is not None
        worker.run()

        card_container = dialog.discover_list.widget()
        install_buttons = [
            b
            for b in card_container.findChildren(
                __import__("PySide6.QtWidgets", fromlist=["QPushButton"]).QPushButton
            )
            if b.text() == t("plugins.install")
        ]
        assert len(install_buttons) == 1
        button = install_buttons[0]
        dialog.install_plugin(entry, button)

        install_worker = dialog._install_worker
        assert install_worker is not None
        install_worker.run()

        assert emitted == [True]
        # A completion summary is shown for the successful install.
        assert len(summaries) == 1
        # After success the button text/labels were rebuilt without error.
        assert dialog._install_worker is None


@pytest.mark.gui
def test_failed_install_restores_state_and_shows_error(qapp, frozen_thread_pool, monkeypatch):
    monkeypatch.setattr(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.read_active_versions",
        lambda: {},
    )
    monkeypatch.setattr(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.read_disabled_ids",
        lambda: set(),
    )
    dialog = PluginManagerDialog(fetcher=registry_fetcher())
    entry = VALID_REGISTRY["plugins"][0]
    shown = []

    class FakeBox:
        Warning = 3

        @staticmethod
        def warning(*args, **kwargs):
            shown.append(args)

    with mock.patch(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.load_installed_plugins"
    ) as loader, mock.patch(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.install_plugin_from_registry",
        side_effect=RuntimeError("Manifest SHA-256 mismatch"),
    ), mock.patch(
        "PySide6.QtWidgets.QMessageBox", FakeBox
    ):
        loader.return_value = SimpleNamespace(plugins=[])
        dialog._on_registry_loaded(json.loads(json.dumps(VALID_REGISTRY)), "network")

        card_container = dialog.discover_list.widget()
        from PySide6.QtWidgets import QPushButton

        button = next(
            b for b in card_container.findChildren(QPushButton)
            if b.text() == t("plugins.install")
        )
        dialog.install_plugin(entry, button)
        worker = dialog._install_worker
        worker.run()

        assert dialog._install_worker is None
        assert len(shown) == 1
        assert t("plugins.verification_failed").format(name="") in str(shown[0])


@pytest.mark.gui
def test_removal_confirmation_path(qapp):
    dialog = PluginManagerDialog()
    emitted = []
    dialog.plugins_changed.connect(lambda: emitted.append(True))

    installed_plugin = SimpleNamespace(
        manifest=SimpleNamespace(id="org.hpcclient.truba", name="TRUBA", version="1.0.0")
    )
    removed = []
    answered = []

    class FakeBox:
        Yes = 1
        No = 0

        @staticmethod
        def question(*args, **kwargs):
            answered.append(args)
            return FakeBox.Yes if kwargs.get("answer_yes") else FakeBox.Yes

        @staticmethod
        def warning(*args, **kwargs):
            pass

    with mock.patch(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.load_installed_plugins"
    ) as loader, mock.patch(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.remove_plugin",
        side_effect=lambda pid: removed.append(pid) or ["1.0.0"],
    ), mock.patch("PySide6.QtWidgets.QMessageBox", FakeBox):
        loader.return_value = SimpleNamespace(plugins=[installed_plugin])
        dialog.rebuild_tabs()

        dialog.remove_plugin("org.hpcclient.truba", "TRUBA")

    assert removed == ["org.hpcclient.truba"]
    assert len(answered) == 1
    assert "TRUBA" in answered[0][2]
    assert emitted == [True]


@pytest.mark.gui
def test_removal_cancelled_does_not_remove(qapp):
    dialog = PluginManagerDialog()
    removed = []

    class FakeBox:
        Yes = 1
        No = 0

        @staticmethod
        def question(*args, **kwargs):
            return FakeBox.No

    with mock.patch(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.load_installed_plugins"
    ) as loader, mock.patch(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.remove_plugin",
        side_effect=lambda pid: removed.append(pid),
    ), mock.patch("PySide6.QtWidgets.QMessageBox", FakeBox):
        loader.return_value = SimpleNamespace(plugins=[])
        dialog.rebuild_tabs()
        dialog.remove_plugin("org.hpcclient.truba", "TRUBA")

    assert removed == []


@pytest.mark.gui
def test_updates_tab_lists_newer_compatible_version(qapp):
    dialog = PluginManagerDialog()
    dialog._registry = json.loads(json.dumps(VALID_REGISTRY))
    dialog._registry_source = "network"

    dialog._populate_updates({"org.hpcclient.truba": "0.9.0"})
    container = dialog.updates_list.widget()
    text = "\n".join(
        label.text()
        for label in container.findChildren(type(dialog.status_label))
    )
    assert "0.9.0" in text and "1.0.0" in text

    # Up-to-date plugins produce the empty-state message.
    dialog._populate_updates({"org.hpcclient.truba": "1.0.0"})
    text = "\n".join(
        label.text()
        for label in dialog.updates_list.widget().findChildren(type(dialog.status_label))
    )
    assert t("plugins.no_updates") in text


@pytest.mark.gui
def test_search_filter_hides_non_matching_cards(qapp):
    dialog = PluginManagerDialog()
    apply_registry(dialog)

    container = dialog.discover_list.widget()
    cards = [
        child for child in container.findChildren(__import__("PySide6.QtWidgets", fromlist=["QFrame"]).QFrame)
        if child.property("searchText")
    ]
    assert len(cards) == 2

    dialog.search_box.setText("TRUBA")
    visibility = {card.property("searchText"): card.isVisibleTo(container) for card in cards}
    truba_cards = [v for k, v in visibility.items() if "truba" in k]
    future_cards = [v for k, v in visibility.items() if "future" in k.lower()]
    assert any(truba_cards)
    assert all(not v for v in future_cards)

    dialog.search_box.setText("")
    assert all(card.isVisibleTo(container) for card in cards)
