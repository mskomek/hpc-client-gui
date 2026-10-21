from __future__ import annotations

import hashlib
import json
import unittest.mock as mock
from types import SimpleNamespace
from PySide6.QtGui import QDesktopServices
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
def _registry_fetch_result(source="network"):
    from hpc_gui.plugins.registry_client import RegistryFetchResult

    return RegistryFetchResult(
        registry=json.loads(json.dumps(VALID_REGISTRY)),
        source=source,
        fetched_at="now",
    )
def make_entry(
    plugin_id: str,
    name: str,
    version: str,
    type_: str,
    requires_app: str = ">=1.4.0",
) -> dict:
    return {
        "id": plugin_id,
        "name": name,
        "version": version,
        "plugin_api": 1,
        "type": type_,
        "description": f"{name} plugin.",
        "publisher": "HPC Client GUI",
        "requires_app": requires_app,
        "manifest_path": f"plugins/{plugin_id.split('.')[-1]}/{version}/manifest.json",
        "manifest_sha256": hashlib.sha256(f"{plugin_id}{version}".encode()).hexdigest(),
        "official": True,
    }
def grouped_registry() -> dict:
    return {
        "schema_version": 1,
        "plugin_api": 1,
        "repository": VALID_REGISTRY["repository"],
        "plugins": [
            make_entry("org.hpcclient.truba", "TRUBA", "1.0.0", "cluster-profile"),
            make_entry("org.hpcclient.fluent", "Fluent Tools", "0.2.0", "lint-rules"),
            make_entry("org.hpcclient.fluent", "Fluent Tools", "0.1.0", "lint-rules"),
        ],
    }
def discover_labels(dialog: PluginManagerDialog):
    return [
        label.text()
        for label in dialog.discover_list.widget().findChildren(type(dialog.status_label))
    ]
def discover_buttons(dialog: PluginManagerDialog):
    from PySide6.QtWidgets import QPushButton

    return list(dialog.discover_list.widget().findChildren(QPushButton))
def discover_cards(dialog: PluginManagerDialog):
    from PySide6.QtWidgets import QFrame

    return [
        card
        for card in dialog.discover_list.widget().findChildren(QFrame)
        if card.property("searchText")
    ]
def _buttons_of_card(dialog: PluginManagerDialog, needle: str):
    from PySide6.QtWidgets import QPushButton

    buttons = []
    for card in discover_cards(dialog):
        if needle in str(card.property("searchText")):
            buttons.extend(card.findChildren(QPushButton))
    return buttons
def _make_installed_dialog(qapp, versions, active_version="1.9.0"):
    dialog = PluginManagerDialog()
    dialog._installed_versions = SimpleNamespace(
        plugins=[
            SimpleNamespace(
                manifest=SimpleNamespace(
                    id="org.hpcclient.multi",
                    name="Multi",
                    version=active_version,
                )
            )
        ],
        problems=[],
    )
    active_patch = mock.patch(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.read_active_versions",
        return_value={"org.hpcclient.multi": active_version},
    )
    state_patch = mock.patch(
        "hpc_gui.plugins.state.read_installed_state",
        return_value={
            "org.hpcclient.multi": {
                "versions": list(versions),
                "installed_at": "",
                "manifest_hashes": {},
                "migrated": [],
            }
        },
    )
    with active_patch, state_patch:
        dialog._populate_installed({"org.hpcclient.multi": active_version})
    return dialog
def _installed_card_widgets(dialog):
    from PySide6.QtWidgets import QComboBox, QPushButton

    container = dialog.installed_list.widget()
    combos = container.findChildren(QComboBox)
    buttons = container.findChildren(QPushButton)
    return combos, buttons

__all__ = [
    'hashlib',
    'json',
    'mock',
    'SimpleNamespace',
    'QDesktopServices',
    'pytest',
    'load_language',
    't',
    'PluginManagerDialog',
    'OFFICIAL_RAW_BASE',
    'OFFICIAL_REGISTRY_URL',
    'VALID_REGISTRY',
    'qapp',
    'registry_fetcher',
    'make_fetch_result',
    '_FakePool',
    'frozen_thread_pool',
    'apply_registry',
    '_registry_fetch_result',
    'make_entry',
    'grouped_registry',
    'discover_labels',
    'discover_buttons',
    'discover_cards',
    '_buttons_of_card',
    '_make_installed_dialog',
    '_installed_card_widgets',
]
