"""Plugin Manager registry refresh, status, and entry-point UI tests."""

from __future__ import annotations

import json
import unittest.mock as mock
from types import SimpleNamespace

import pytest
from PySide6.QtGui import QDesktopServices

pytest_plugins = ("support.plugin_manager_ui_fixtures",)

from hpc_gui.core.i18n import t
from hpc_gui.ui.dialogs.plugin_manager_dialog import PluginManagerDialog
from support.plugin_manager_ui import (
    VALID_REGISTRY,
    apply_registry,
    _registry_fetch_result,
    registry_fetcher,
)

@pytest.mark.gui
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


@pytest.mark.gui
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


@pytest.mark.gui
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


@pytest.mark.gui
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


@pytest.mark.gui
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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.gui
def test_plugins_button_exists(qapp):
    from unittest.mock import patch

    with patch("hpc_gui.ui.main_window.QTimer.singleShot"):
        from hpc_gui.ui.main_window import MainWindow

        window = MainWindow()
        try:
            # Wave 71 redesign moved plugins from top-right button farm to Plugins menu
            # Old test expected _plugins_btn, new code should have _plugins_menu and actions
            assert hasattr(window, "_plugins_menu")
            assert t("menu.plugins") in window._plugins_menu.title() or "Plugins" in window._plugins_menu.title()
            assert hasattr(window, "_act_plugins_discover")
            assert hasattr(window, "_act_plugins_installed")
        finally:
            window.graceful_shutdown()
            window.close()
            window.deleteLater()


@pytest.mark.gui
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


@pytest.mark.gui
def test_mocked_registry_populates_discover(qapp, monkeypatch):
    monkeypatch.setattr(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.read_active_versions",
        lambda: {},
    )
    monkeypatch.setattr(
        "hpc_gui.ui.dialogs.plugin_manager_dialog.read_disabled_ids",
        lambda: set(),
    )
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


@pytest.mark.gui
def test_cached_status_shown_for_cache_source(qapp):
    dialog = PluginManagerDialog()
    try:
        apply_registry(dialog, source="cache")
        assert t("plugins.status_cached") in dialog.status_label.text()
    finally:
        dialog.deleteLater()
