import pytest

from hpc_gui.wx_plugins import WxPluginManagerModel


def test_plugin_cache_install_disable_enable_and_trusted_tool():
    installed = []
    model = WxPluginManagerModel(install=installed.append)
    model.set_registry([{"id": "org.example.tool", "name": "Tool", "version": "1.0", "compatible": True}], "cache")
    assert model.registry_source == "cache" and model.cards[0].name == "Tool"
    model.install_or_update({"id": "org.example.tool", "version": "1.1"})
    assert installed[0]["version"] == "1.1"
    manifest = {"id": "org.hpcclient.ansyslint", "plugin_api": 2, "capabilities": ["linter-tool"], "publisher": "HPC Client GUI", "entrypoints": {"linter_engine": "engine/ansys_lint/__init__.py"}}
    opened = []
    model.open_trusted_tool(manifest, opened.append)
    assert opened and opened[0]["id"] == "org.hpcclient.ansyslint"


def test_trusted_tool_rejection_is_fail_closed():
    model = WxPluginManagerModel()
    with pytest.raises(PermissionError):
        model.open_trusted_tool({"id": "org.example.bad"}, lambda value: value)


def test_plugin_lifecycle_actions(monkeypatch):
    calls = []
    monkeypatch.setattr("hpc_gui.wx_plugins.activate_version", lambda *args, **kwargs: calls.append(("rollback", args)))
    monkeypatch.setattr("hpc_gui.wx_plugins.set_plugin_disabled", lambda *args, **kwargs: calls.append(("enabled", args)))
    monkeypatch.setattr("hpc_gui.wx_plugins.remove_plugin", lambda *args, **kwargs: ["1.0"])
    model = WxPluginManagerModel()
    model.rollback("p", "1.0")
    model.set_enabled("p", False)
    assert model.remove("p") == ["1.0"] and [call[0] for call in calls] == ["rollback", "enabled"]
