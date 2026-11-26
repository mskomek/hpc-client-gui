"""Wave 05 catalogue cases migrated to the actual wx manager model."""
from hpc_gui.core.i18n import load_language, t
from hpc_gui.plugins.state import record_installed_version
from hpc_gui.wx_plugins import WxPluginManagerModel

FLUENT = "org.hpcclient.fluent"
TRUBA = "org.hpcclient.truba"
FUTURE = "org.hpcclient.future"


def entry(pid, name, version, capability, requires=">=1.4.0"):
    return {"id": pid, "name": name, "version": version, "type": capability,
            "requires_app": requires, "publisher": "HPC Client GUI",
            "description": f"{name} plugin."}


def basic():
    return {"plugins": [entry(TRUBA, "TRUBA", "1.0.0", "cluster-profile"),
                        entry(FUTURE, "Future", "9.9.9", "lint-rules", ">=99.0.0")]}


def grouped():
    return {"plugins": [entry(TRUBA, "TRUBA", "1.0.0", "cluster-profile"),
                        entry(FLUENT, "Fluent Tools", "0.2.0", "lint-rules"),
                        entry(FLUENT, "Fluent Tools", "0.1.0", "lint-rules")]}


def build(tmp_path, registry, active=None, disabled=()):
    model = WxPluginManagerModel(root=tmp_path, app_version="2.0.0")
    for pid, version in (active or {}).items():
        record_installed_version(pid, version, root=tmp_path)
    for pid in disabled:
        model.set_enabled(pid, False)
    model.build_cards_from_registry(registry, "network")
    return model


def find(model, pid):
    return next(card for card in model.cards if card.plugin_id == pid)


def test_mocked_registry_populates_discover(tmp_path):
    model = build(tmp_path, basic())
    assert model.registry_source == "network"
    assert {c.plugin_id for c in model.filtered_cards()} == {TRUBA, FUTURE}
    assert find(model, TRUBA).compatible and not find(model, TRUBA).installed
    assert not find(model, FUTURE).compatible


def test_updates_tab_lists_newer_compatible_version(tmp_path):
    model = build(tmp_path, basic(), {TRUBA: "0.9.0"})
    update, = model.filtered_cards("updates")
    assert (update.active_version, update.version) == ("0.9.0", "1.0.0")
    record_installed_version(TRUBA, "1.0.0", root=tmp_path)
    model.reload_installed()
    assert model.filtered_cards("updates") == ()


def test_search_filter_hides_non_matching_cards(tmp_path):
    model = build(tmp_path, basic())
    assert len(model.filtered_cards()) == 2
    assert [c.plugin_id for c in model.filtered_cards(needle="TRUBA")] == [TRUBA]
    assert len(model.filtered_cards(needle="")) == 2


def test_discover_groups_multiple_versions_under_one_card(tmp_path):
    model = build(tmp_path, grouped())
    assert len(model.cards) == 2
    card = find(model, FLUENT)
    assert card.version == "0.2.0"
    assert model.other_versions[FLUENT] == ("0.1.0",)
    assert "0.1.0" in model.details_for(card)


def test_discover_selects_latest_compatible_with_incompatible_newer(tmp_path):
    registry = grouped()
    registry["plugins"].append(entry(FLUENT, "Fluent Tools", "9.9.9", "lint-rules", ">=99.0.0"))
    model = build(tmp_path, registry)
    assert len(model.cards) == 2
    assert find(model, FLUENT).version == "0.2.0"
    assert all(card.compatible for card in model.cards)
    assert all(card.version != "9.9.9" for card in model.cards)


def test_discover_shows_only_incompatible_state_when_nothing_compatible(tmp_path):
    model = build(tmp_path, {"plugins": [entry(FUTURE, "Future", "2.0.0", "lint-rules", ">=99.0.0")]})
    card, = model.cards
    assert not card.compatible


def test_discover_update_detection(tmp_path):
    model = build(tmp_path, grouped(), {FLUENT: "0.1.0"})
    assert find(model, FLUENT).update_available
    assert find(model, FLUENT).installed
    assert model.filtered_cards("updates") == (find(model, FLUENT),)


def test_discover_latest_version_installed_shows_no_update(tmp_path):
    model = build(tmp_path, grouped(), {FLUENT: "0.2.0"})
    assert find(model, FLUENT).installed and not find(model, FLUENT).update_available


def test_discover_newer_active_version_gets_no_update_offer(tmp_path):
    model = build(tmp_path, grouped(), {FLUENT: "9.0.0"})
    assert find(model, FLUENT).active_version == "9.0.0"
    assert not find(model, FLUENT).update_available


def test_discover_disabled_plugin_state(tmp_path):
    model = build(tmp_path, grouped(), {FLUENT: "0.2.0"}, [FLUENT])
    load_language("en")
    card = find(model, FLUENT)
    assert not card.enabled
    assert t("plugins.installed_disabled") in model.details_for(card)


def test_search_filter_after_grouping(tmp_path):
    model = build(tmp_path, grouped())
    for needle in ("fluent", "0.1.0"):
        assert [c.plugin_id for c in model.filtered_cards(needle=needle)] == [FLUENT]
    assert len(model.filtered_cards()) == 2


def test_updates_tab_uses_grouped_latest(tmp_path):
    model = build(tmp_path, grouped(), {FLUENT: "0.1.0"})
    update, = model.filtered_cards("updates")
    assert (update.active_version, update.version) == ("0.1.0", "0.2.0")
    record_installed_version(FLUENT, "0.2.0", root=tmp_path)
    model.reload_installed()
    assert model.filtered_cards("updates") == ()
