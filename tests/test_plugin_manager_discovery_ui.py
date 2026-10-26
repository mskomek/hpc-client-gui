"""Plugin Manager catalog grouping, compatibility, and discovery UI tests."""

from __future__ import annotations

import hashlib
import unittest.mock as mock

import pytest

pytest_plugins = ("support.plugin_manager_ui_fixtures",)

from hpc_gui.core.i18n import load_language, t
from hpc_gui.ui.dialogs.plugin_manager_dialog import PluginManagerDialog
from support.plugin_manager_ui import VALID_REGISTRY

@pytest.mark.gui
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


@pytest.mark.gui
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


@pytest.mark.gui
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


@pytest.mark.gui
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


@pytest.mark.gui
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


@pytest.mark.gui
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


@pytest.mark.gui
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


@pytest.mark.gui
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


@pytest.mark.gui
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


@pytest.mark.gui
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


@pytest.mark.unit
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


@pytest.mark.contract
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
