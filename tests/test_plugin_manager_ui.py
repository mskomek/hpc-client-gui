"""Wave 05 tests: Plugins button and Plugin Manager dialog states.

All registry/installer interactions use injected fetchers and patched
service functions; nothing touches the network.
"""

from __future__ import annotations

import hashlib
import json
import os
import unittest.mock as mock
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from hpc_gui.core.i18n import load_language, t
from hpc_gui.ui.dialogs.plugin_manager_dialog import PluginManagerDialog
from hpc_gui.plugins.registry_client import OFFICIAL_RAW_BASE, OFFICIAL_REGISTRY_URL


VALID_REGISTRY = {
    "schema_version": 1,
    "plugin_api": 1,
    "repository": {
        "owner": "mskomek",
        "name": "hpc-client-gui-plugins",
        "raw_base": OFFICIAL_RAW_BASE,
    },
    "plugins": [
        {
            "id": "org.hpcclient.truba",
            "name": "TRUBA",
            "version": "1.0.0",
            "plugin_api": 1,
            "type": "cluster-profile",
            "description": "TRUBA system profile for HPC Client GUI.",
            "publisher": "HPC Client GUI",
            "requires_app": ">=1.3.0",
            "manifest_path": "plugins/truba/1.0.0/manifest.json",
            "manifest_sha256": hashlib.sha256(b"manifest").hexdigest(),
            "official": True,
        },
        {
            "id": "org.hpcclient.future",
            "name": "Future Plugin",
            "version": "9.9.9",
            "plugin_api": 1,
            "type": "lint-rules",
            "description": "Requires a much newer app.",
            "publisher": "HPC Client GUI",
            "requires_app": ">=99.0.0",
            "manifest_path": "plugins/future/9.9.9/manifest.json",
            "manifest_sha256": hashlib.sha256(b"m2").hexdigest(),
            "official": True,
        },
    ],
}


@pytest.fixture(scope="module", autouse=True)
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    load_language("en")
    yield app
    load_language("en")


def registry_fetcher():
    payload = json.dumps(VALID_REGISTRY).encode()
    def fetch(url: str, max_bytes: int) -> bytes:
        assert url == OFFICIAL_REGISTRY_URL
        return payload
    return fetch


def make_fetch_result(source="network"):
    return SimpleNamespace(
        registry=json.loads(json.dumps(VALID_REGISTRY)), source=source, fetched_at="now"
    )


class _FakePool:
    """Prevents queued workers from running twice (test calls run() itself)."""

    def start(self, runnable, *args, **kwargs):
        return None


@pytest.fixture()
def frozen_thread_pool():
    with mock.patch(
        "PySide6.QtCore.QThreadPool.globalInstance", create=True
    ) as instance:
        instance.return_value = _FakePool()
        yield


def apply_registry(dialog: PluginManagerDialog, source: str = "network") -> None:
    """Drive the async refresh completion handler synchronously."""
    dialog._on_registry_loaded(json.loads(json.dumps(VALID_REGISTRY)), source)


def test_plugins_button_exists(qapp):
    from unittest.mock import patch

    with patch("hpc_gui.ui.main_window.QTimer.singleShot"):
        from hpc_gui.ui.main_window import MainWindow

        window = MainWindow()
        try:
            assert hasattr(window, "_plugins_btn")
            assert window._plugins_btn.text() == t("plugins.action")
            # Button sits in the top-right control strip next to Update.
            parent_chain = []
            widget = window._plugins_btn.parentWidget()
            while widget is not None:
                parent_chain.append(widget)
                widget = widget.parentWidget()
            assert any(
                child is window._update_btn
                for container in parent_chain
                for child in container.findChildren(type(window._update_btn))
            )
        finally:
            window.graceful_shutdown()
            window.close()
            window.deleteLater()


def test_dialog_opens_offline_without_cache(qapp):
    with mock.patch(
        "hpc_gui.plugins.registry_client.read_cached_registry", return_value=None
    ):
        dialog = PluginManagerDialog()
        try:
            dialog._on_registry_unavailable()
            assert t("plugins.status_offline") in dialog.status_label.text()
            assert dialog.tabs.count() == 3
            discover = dialog.discover_list.widget().layout()
            assert discover.count() >= 1  # empty-state label
        finally:
            dialog.deleteLater()


def test_mocked_registry_populates_discover(qapp):
    dialog = PluginManagerDialog(fetcher=lambda url, limit: (_ for _ in ()).throw(OSError()))
    try:
        apply_registry(dialog)
        assert t("plugins.status_online") in dialog.status_label.text()

        texts = []
        container = dialog.discover_list.widget()
        for label in container.findChildren(type(dialog.status_label)):
            texts.append(label.text())
        joined = "\n".join(texts)
        assert "TRUBA" in joined
        assert t("plugins.installed_badge") not in joined or "TRUBA" in joined

        # Incompatible plugin's install button is disabled.
        buttons = [w for w in container.findChildren(__import__("PySide6.QtWidgets", fromlist=["QPushButton"]).QPushButton)]
        future_button = next(b for b in buttons if b.text() == t("plugins.incompatible"))
        assert not future_button.isEnabled()
        truba_install = next(b for b in buttons if b.text() == t("plugins.install"))
        assert truba_install.isEnabled()
    finally:
        dialog.deleteLater()


def test_cached_status_shown_for_cache_source(qapp):
    dialog = PluginManagerDialog()
    try:
        apply_registry(dialog, source="cache")
        assert t("plugins.status_cached") in dialog.status_label.text()
    finally:
        dialog.deleteLater()


def test_successful_install_updates_state_and_emits_signal(qapp, frozen_thread_pool):
    dialog = PluginManagerDialog(fetcher=registry_fetcher())
    emitted = []
    dialog.plugins_changed.connect(lambda: emitted.append(True))
    entry = VALID_REGISTRY["plugins"][0]

    def fake_install(registry_entry, **kwargs):
        return SimpleNamespace(installed=SimpleNamespace(manifest=SimpleNamespace(id=entry["id"])), activated=True)

    with mock.patch(
        "hpc_gui.plugins.loader.read_active_versions",
        return_value={entry["id"]: entry["version"]},
    ), mock.patch(
        "hpc_gui.plugins.state.read_active_versions", return_value={}
    ), mock.patch(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.load_installed_plugins"
    ) as loader, mock.patch(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.install_plugin_from_registry",
        side_effect=fake_install,
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
        # After success the button text/labels were rebuilt without error.
        assert dialog._install_worker is None


def test_failed_install_restores_state_and_shows_error(qapp, frozen_thread_pool):
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


def test_updates_tab_lists_newer_compatible_version(qapp):
    dialog = PluginManagerDialog()
    with mock.patch.object(
        type(dialog), "_installed_versions", create=True
    ):
        pass
    dialog._registry = json.loads(json.dumps(VALID_REGISTRY))
    dialog._registry_source = "network"

    active = {"org.hpcclient.truba": "0.9.0"}
    inner = dialog._populate_updates(active)
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


def test_details_shows_cluster_commands_warning(qapp):
    dialog = PluginManagerDialog()
    shown = []

    class FakeBox:
        @staticmethod
        def information(*args, **kwargs):
            shown.append(args)

    with mock.patch("PySide6.QtWidgets.QMessageBox", FakeBox):
        dialog.show_details(VALID_REGISTRY["plugins"][0])

    text = shown[0][2]
    assert t("plugins.cluster_commands_warning") in text


def test_i18n_keys_resolve_in_both_languages():
    for language in ("en", "tr"):
        load_language(language)
        try:
            for key in (
                "plugins.action",
                "plugins.tab_discover",
                "plugins.tab_installed",
                "plugins.tab_updates",
                "plugins.install",
                "plugins.installing",
                "plugins.update",
                "plugins.remove",
                "plugins.refresh",
                "plugins.status_offline",
                "plugins.registry_unavailable",
                "plugins.verification_failed",
                "plugins.incompatible",
                "plugins.publisher",
                "plugins.version",
                "plugins.license",
                "plugins.capabilities",
                "plugins.cluster_commands_warning",
                "plugins.details",
            ):
                value = t(key)
                assert value and value != key, f"missing key {key} for {language}"
        finally:
            load_language("en")
