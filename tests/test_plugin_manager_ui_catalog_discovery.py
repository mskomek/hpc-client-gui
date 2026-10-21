"""Wave 05 tests: Plugins button and Plugin Manager dialog states.

All registry/installer interactions use injected fetchers and patched
service functions; nothing touches the network.
"""

from __future__ import annotations

pytest_plugins = ('support.test_plugin_manager_ui_shared',)
from support.test_plugin_manager_ui_shared import (
    PluginManagerDialog,
    VALID_REGISTRY,
    _buttons_of_card,
    apply_registry,
    discover_buttons,
    discover_cards,
    discover_labels,
    grouped_registry,
    json,
    make_entry,
    mock,
    pytest,
    t,
)

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
