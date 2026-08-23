"""Wave 05 tests: Plugins button and Plugin Manager dialog states.

All registry/installer interactions use injected fetchers and patched
service functions; nothing touches the network.
"""

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


def test_first_show_starts_exactly_one_automatic_refresh(qapp, frozen_thread_pool):
    calls = []

    def fake_fetch(**kwargs):
        calls.append(kwargs)
        return _registry_fetch_result()

    dialog = PluginManagerDialog(fetcher=lambda url, limit: b"{}")
    try:
        with mock.patch(
            "hpc_gui.ui.dialogs.plugin_manager_dialog.fetch_registry_with_cache",
            side_effect=fake_fetch,
        ):
            assert t("plugins.status_loading") not in dialog.status_label.text()
            dialog.show()
            qapp.processEvents()
            # One request queued immediately; the loading state is visible
            # while the worker runs.
            assert dialog._refresh_worker is not None
            assert dialog.status_label.text() == t("plugins.status_loading")
            assert not dialog.refresh_button.isEnabled()
            first_worker = dialog._refresh_worker

            # Re-showing the same dialog never duplicates the request.
            dialog.hide()
            dialog.show()
            qapp.processEvents()
            assert len(calls) == 0  # still the single queued worker
            assert dialog._refresh_worker is first_worker

            first_worker.run()
            assert len(calls) == 1
            assert t("plugins.status_online") in dialog.status_label.text()
            assert dialog.refresh_button.isEnabled()
    finally:
        dialog.deleteLater()


def test_refresh_guard_blocks_duplicate_inflight_requests(qapp, frozen_thread_pool):
    dialog = PluginManagerDialog(fetcher=lambda url, limit: b"{}")
    try:
        with mock.patch(
            "hpc_gui.ui.dialogs.plugin_manager_dialog.fetch_registry_with_cache",
            return_value=_registry_fetch_result(),
        ):
            dialog.refresh_registry()
            first_worker = dialog._refresh_worker
            assert first_worker is not None
            # Extra requests while one is in flight are ignored entirely.
            dialog.refresh_registry()
            dialog.refresh_registry()
            assert dialog._refresh_worker is first_worker

            first_worker.run()
            # After completion a manual refresh is possible again.
            dialog.refresh_registry()
            assert dialog._refresh_worker is not first_worker
            dialog._refresh_worker.run()
            assert t("plugins.status_online") in dialog.status_label.text()
    finally:
        dialog.deleteLater()


def test_offline_with_cache_fallback_populates_tabs(qapp, frozen_thread_pool):
    def failing_fetch(**kwargs):
        raise OSError("network down")

    dialog = PluginManagerDialog(fetcher=lambda url, limit: (_ for _ in ()).throw(OSError()))
    try:
        with mock.patch(
            "hpc_gui.ui.dialogs.plugin_manager_dialog.fetch_registry_with_cache",
            side_effect=failing_fetch,
        ), mock.patch(
            "hpc_gui.plugins.registry_client.read_cached_registry",
            return_value=json.loads(json.dumps(VALID_REGISTRY)),
        ):
            dialog.refresh_registry()
            dialog._refresh_worker.run()
            # Network unavailable but a last-known-good cache exists.
            assert t("plugins.status_cached") in dialog.status_label.text()
            assert dialog._registry_source == "cache"
            texts = [
                label.text()
                for label in dialog.discover_list.widget().findChildren(type(dialog.status_label))
                if label.text()
            ]
            assert any("TRUBA" in text for text in texts)
    finally:
        dialog.deleteLater()


def test_offline_without_cache_shows_offline_state(qapp, frozen_thread_pool):
    def failing_fetch(**kwargs):
        raise OSError("network down")

    dialog = PluginManagerDialog(fetcher=lambda url, limit: (_ for _ in ()).throw(OSError()))
    try:
        with mock.patch(
            "hpc_gui.ui.dialogs.plugin_manager_dialog.fetch_registry_with_cache",
            side_effect=failing_fetch,
        ), mock.patch(
            "hpc_gui.plugins.registry_client.read_cached_registry",
            return_value=None,
        ):
            dialog.refresh_registry()
            dialog._refresh_worker.run()
            assert t("plugins.status_offline") in dialog.status_label.text()
            assert dialog.refresh_button.isEnabled()
            discover = dialog.discover_list.widget().layout()
            assert discover.count() >= 1  # empty-state label
    finally:
        dialog.deleteLater()


def test_closing_during_refresh_is_safe(qapp, frozen_thread_pool):
    dialog = PluginManagerDialog(fetcher=lambda url, limit: b"{}")
    dialog.show()
    qapp.processEvents()
    worker = dialog._refresh_worker
    assert worker is not None
    # Close while the worker is still queued, then let the worker finish.
    dialog.reject()
    assert dialog._refresh_worker is None
    worker.run()  # must not raise against the closed dialog
    qapp.processEvents()
    dialog.deleteLater()


def test_request_plugin_action_targets_dedicated_issue_form(qapp):
    from hpc_gui.ui.dialogs.plugin_manager_dialog import PLUGIN_REQUEST_URL

    assert PLUGIN_REQUEST_URL == (
        "https://github.com/mskomek/hpc-client-gui-plugins/issues/new"
        "?template=plugin-request.yml"
    )
    dialog = PluginManagerDialog()
    try:
        opened = []
        with mock.patch.object(QDesktopServices, "openUrl", staticmethod(lambda url: opened.append(url) or True)):
            assert dialog.open_plugin_requests() is True
        assert opened == [PLUGIN_REQUEST_URL]

        # Non-allowed destinations are refused without opening anything.
        with mock.patch.object(QDesktopServices, "openUrl", staticmethod(lambda url: True)):
            assert dialog._is_allowed_plugin_request_url("https://evil.example.com/x") is False

        with mock.patch.object(QDesktopServices, "openUrl", staticmethod(lambda url: False)):
            shown = []

            class FakeBox:
                Warning = 3

                @staticmethod
                def warning(*args, **kwargs):
                    shown.append(args)

            with mock.patch("PySide6.QtWidgets.QMessageBox", FakeBox):
                assert dialog.open_plugin_requests() is False
            assert len(shown) == 1
    finally:
        dialog.deleteLater()


def test_capability_badges_use_translated_labels(qapp):
    registry = grouped_registry()
    fluent = next(e for e in registry["plugins"] if e["id"] == "org.hpcclient.fluent")
    fluent["capabilities"] = ["lint-rules", "job-template"]
    dialog = PluginManagerDialog()
    try:
        dialog._registry = registry
        dialog._registry_source = "network"
        dialog._populate_discover({})
        texts = discover_labels(dialog)
        assert any(t("plugins.capability_lint_rules") in text for text in texts)
        assert any(t("plugins.capability_job_templates") in text for text in texts)
        # Raw identifiers are not shown as primary UI text.
        joined = "\n".join(texts)
        assert "lint-rules" not in joined
        assert "job-template\n" not in joined and not any(
            text.strip().endswith("job-template") for text in texts
        )
    finally:
        dialog.deleteLater()


def test_install_summary_reports_capability_counts(qapp, frozen_thread_pool):
    dialog = PluginManagerDialog(fetcher=registry_fetcher())
    entry = VALID_REGISTRY["plugins"][0]
    result = SimpleNamespace(
        installed=SimpleNamespace(
            manifest=SimpleNamespace(id=entry["id"], name="TRUBA"),
            cluster_profiles=(SimpleNamespace(),),
            lint_index=None,
            job_templates_index={"templates": [{}, {}, {}, {}]},
        ),
        activated=True,
    )
    dialog._last_install_result = result
    text = dialog._install_summary_text(entry)
    assert "TRUBA" in text
    assert "1" in text and "4" in text

    # Without detailed counts the generic message is used.
    dialog._last_install_result = SimpleNamespace(installed=None, activated=True)
    generic = dialog._install_summary_text(entry)
    assert generic == t("plugins.install_generic").format(name="TRUBA")


def test_details_show_source_and_installed_state(qapp):
    shown = []

    class FakeBox:
        @staticmethod
        def information(*args, **kwargs):
            shown.append(args)

    dialog = PluginManagerDialog()
    try:
        with mock.patch(
            "hpc_gui.ui.dialogs.plugin_manager_dialog.read_active_versions",
            return_value={"org.hpcclient.truba": "1.0.0"},
        ), mock.patch(
            "PySide6.QtWidgets.QMessageBox", FakeBox
        ):
            dialog.show_details(VALID_REGISTRY["plugins"][0], ["0.9.0"])
        text = shown[0][2]
        assert t("plugins.source_official_registry") in text
        assert t("plugins.installed_active") in text
        assert "0.9.0" in text
        assert "org.hpcclient.truba" in text
    finally:
        dialog.deleteLater()


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


def test_discover_groups_multiple_versions_under_one_card(qapp):
    dialog = PluginManagerDialog()
    try:
        dialog._registry = grouped_registry()
        dialog._registry_source = "network"
        dialog._populate_discover({})

        cards = discover_cards(dialog)
        assert len(cards) == 2  # one per plugin id, not per version

        texts = discover_labels(dialog)
        assert any("v0.2.0" in text for text in texts)
        assert not any(
            text.startswith("Fluent Tools v0.1.0") for text in texts
        )
        # Older version remains visible in the catalogue details row.
        assert any(t("plugins.other_versions_catalog") in text and "0.1.0" in text for text in texts)
    finally:
        dialog.deleteLater()


def test_discover_selects_latest_compatible_with_incompatible_newer(qapp):
    registry = grouped_registry()
    registry["plugins"].append(
        make_entry(
            "org.hpcclient.fluent", "Fluent Tools", "9.9.9", "lint-rules",
            requires_app=">=99.0.0",
        )
    )
    dialog = PluginManagerDialog()
    try:
        dialog._registry = registry
        dialog._registry_source = "network"
        dialog._populate_discover({})

        cards = discover_cards(dialog)
        assert len(cards) == 2
        texts = discover_labels(dialog)
        # The compatible 0.2.0 is primary; the incompatible 9.9.9 does not
        # shadow it and is not offered as an installable card.
        assert any("v0.2.0" in text for text in texts)
        assert not any("v9.9.9" in text for text in texts)

        install_buttons = [b for b in discover_buttons(dialog) if b.text() == t("plugins.install")]
        assert all(b.isEnabled() for b in install_buttons)
    finally:
        dialog.deleteLater()


def test_discover_shows_only_incompatible_state_when_nothing_compatible(qapp):
    registry = {
        **grouped_registry(),
        "plugins": [make_entry("org.hpcclient.future", "Future", "2.0.0", "lint-rules", ">=99.0.0")],
    }
    dialog = PluginManagerDialog()
    try:
        dialog._registry = registry
        dialog._registry_source = "network"
        dialog._populate_discover({})
        buttons = discover_buttons(dialog)
        incompatible = [b for b in buttons if b.text() == t("plugins.incompatible")]
        assert incompatible and not incompatible[0].isEnabled()
    finally:
        dialog.deleteLater()


def test_discover_update_detection(qapp):
    dialog = PluginManagerDialog()
    try:
        dialog._registry = grouped_registry()
        dialog._registry_source = "network"
        dialog._populate_discover({"org.hpcclient.fluent": "0.1.0"})

        texts = discover_labels(dialog)
        assert any(t("plugins.update_available") in text for text in texts)
        fluent_buttons = _buttons_of_card(dialog, "fluent")
        assert any(b.text() == t("plugins.update") for b in fluent_buttons)
        assert not any(b.text() == t("plugins.install") for b in fluent_buttons)
    finally:
        dialog.deleteLater()


def test_discover_latest_version_installed_shows_no_update(qapp):
    dialog = PluginManagerDialog()
    try:
        dialog._registry = grouped_registry()
        dialog._registry_source = "network"
        # Active 0.2.0 (latest): installed badge only, never a downgrade.
        dialog._populate_discover({"org.hpcclient.fluent": "0.2.0"})

        texts = discover_labels(dialog)
        assert any(t("plugins.installed_badge") in text for text in texts)
        assert not any(t("plugins.update_available") in text for text in texts)
        assert not any(
            b.text() == t("plugins.update")
            for b in _buttons_of_card(dialog, "fluent")
        )
    finally:
        dialog.deleteLater()


def test_discover_newer_active_version_gets_no_update_offer(qapp):
    dialog = PluginManagerDialog()
    try:
        dialog._registry = grouped_registry()
        dialog._registry_source = "network"
        # A newer active version than the registry must not offer updates
        # (no downgrade presented as an update).
        dialog._populate_discover({"org.hpcclient.fluent": "9.0.0"})
        assert not any(
            b.text() == t("plugins.update")
            for b in _buttons_of_card(dialog, "fluent")
        )
    finally:
        dialog.deleteLater()


def test_discover_disabled_plugin_state(qapp):
    dialog = PluginManagerDialog()
    try:
        dialog._registry = grouped_registry()
        dialog._registry_source = "network"
        with mock.patch(
            "hpc_gui.ui.dialogs.plugin_manager_dialog.read_disabled_ids",
            return_value={"org.hpcclient.fluent"},
        ):
            dialog._populate_discover({"org.hpcclient.fluent": "0.2.0"})
        texts = discover_labels(dialog)
        assert any(t("plugins.disabled_label") in text for text in texts)
    finally:
        dialog.deleteLater()


def test_search_filter_after_grouping(qapp):
    dialog = PluginManagerDialog()
    try:
        dialog._registry = grouped_registry()
        dialog._registry_source = "network"
        dialog._populate_discover({})

        cards = discover_cards(dialog)
        dialog.search_box.setText("fluent")
        visible = {c.property("searchText"): c.isVisibleTo(c.parentWidget()) for c in cards}
        assert any(v and "fluent" in k for k, v in visible.items())
        assert all(not v for k, v in visible.items() if "truba" in k)

        # Old versions are searchable too.
        dialog.search_box.setText("0.1.0")
        matches = [c for c in cards if c.isVisibleTo(c.parentWidget())]
        assert len(matches) == 1 and "fluent" in matches[0].property("searchText")

        dialog.search_box.setText("")
        assert all(c.isVisibleTo(c.parentWidget()) for c in cards)
    finally:
        dialog.deleteLater()


def test_updates_tab_uses_grouped_latest(qapp):
    dialog = PluginManagerDialog()
    dialog._registry = grouped_registry()
    dialog._registry_source = "network"

    dialog._populate_updates({"org.hpcclient.fluent": "0.1.0"})
    container = dialog.updates_list.widget()
    text = "\n".join(label.text() for label in container.findChildren(type(dialog.status_label)))
    assert "0.1.0" in text and "0.2.0" in text

    dialog._populate_updates({"org.hpcclient.fluent": "0.2.0"})
    text = "\n".join(
        label.text() for label in dialog.updates_list.widget().findChildren(type(dialog.status_label))
    )
    assert t("plugins.no_updates") in text


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
