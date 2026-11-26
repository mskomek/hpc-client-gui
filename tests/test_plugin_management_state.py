"""Portable state readback and version/details contracts for the native manager."""
from hpc_gui.plugins.state import record_installed_version
from hpc_gui.plugins.storage import read_active_versions
from hpc_gui.wx_plugins import WxPluginManagerModel


def test_model_reloads_all_registry_versions_and_installed_state(tmp_path):
    pid = "org.example.tool"
    registry = {"plugins": [
        {"id": pid, "name": "Example", "version": version, "requires_app": ">=1.0.0",
         "type": "cluster-profile", "description": "Test", "publisher": "Example"}
        for version in ("1.0.0", "2.0.0")
    ]}
    model = WxPluginManagerModel(root=tmp_path, app_version="2.0.0")
    model.build_cards_from_registry(registry, "cache")
    assert not model.cards[0].installed
    record_installed_version(pid, "1.0.0", root=tmp_path)
    record_installed_version(pid, "2.0.0", root=tmp_path, activate=False)
    model.reload_installed()
    card = model.cards[0]
    assert card.installed and card.update_available and card.active_version == "1.0.0"
    assert model.installed_versions(pid) == ("2.0.0", "1.0.0")
    assert model.other_versions[pid] == ("1.0.0",)
    assert "1.0.0" in model.details_for(card)
    model.set_enabled(pid, False)
    model.reload_installed()
    assert not model.cards[0].enabled
    model.set_enabled(pid, True)
    model.reload_installed()
    assert model.cards[0].enabled
    model.remove(pid)
    model.reload_installed()
    assert not model.cards[0].installed and not model.installed_versions(pid)
    assert pid not in read_active_versions(tmp_path)


def test_version_switch_rejects_uninstalled_target(tmp_path):
    import pytest

    model = WxPluginManagerModel(root=tmp_path)
    record_installed_version("org.example.tool", "1.0.0", root=tmp_path)
    with pytest.raises(ValueError, match="not installed"):
        model.rollback("org.example.tool", "9.9.9")
    assert read_active_versions(tmp_path)["org.example.tool"] == "1.0.0"



def test_real_packages_activation_failure_and_corruption_readback(tmp_path):
    import pytest
    from test_plugin_integrity import install
    from hpc_gui.plugins.storage import plugin_package_dir

    pid = "org.hpcclient.truba"
    install(tmp_path, version="1.0.0")
    install(tmp_path, version="2.0.0")
    model = WxPluginManagerModel(root=tmp_path)
    model.build_cards_from_registry(None, "offline")
    assert not model.problems
    assert model.cards[0].name == "TRUBA"
    model.rollback(pid, "1.0.0")
    model.reload_installed()
    assert model.cards[0].active_version == "1.0.0"
    payload = plugin_package_dir(pid, "2.0.0", tmp_path) / "cluster-profile.json"
    payload.write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="failed validation"):
        model.rollback(pid, "2.0.0")
    assert read_active_versions(tmp_path)[pid] == "1.0.0"
    assert payload.exists()
    active_payload = plugin_package_dir(pid, "1.0.0", tmp_path) / "cluster-profile.json"
    active_payload.write_text("tampered", encoding="utf-8")
    model.reload_installed()
    assert model.cards[0].problem and len(model.problems) == 1
    assert "integrity check failed" in model.details_for(model.cards[0])
    assert model.installed_versions(pid) == ("2.0.0", "1.0.0")
