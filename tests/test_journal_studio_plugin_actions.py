from types import SimpleNamespace

from hpc_gui.services.plugin_menu_actions import can_execute_action, dispatch_plugin_menu_action


def _plugin(plugin_id, capabilities):
    return SimpleNamespace(manifest=SimpleNamespace(id=plugin_id, capabilities=tuple(capabilities)))


def test_journal_studio_actions_are_reserved_and_capability_checked():
    own = _plugin("org.hpcclient.ansysjournalstudio", ["application-tools"])
    other = _plugin("org.example.other", ["application-tools"])
    assert can_execute_action("journal_studio.open", own) == (True, "")
    allowed, reason = can_execute_action("journal_studio.open", other)
    assert not allowed
    assert "reserved" in reason
    assert can_execute_action("journal_studio.open", _plugin(own.manifest.id, []))[0] is False


def test_journal_studio_menu_dispatches_only_to_host_owned_adapter():
    plugin = _plugin("org.hpcclient.ansysjournalstudio", ["application-tools"])
    calls = []
    host = SimpleNamespace(
        run_editor_lint=lambda _plugin_id: False,
        open_journal_studio=lambda selected, action: calls.append((selected, action)) or True,
    )
    assert dispatch_plugin_menu_action("journal_studio.new", plugin, host)
    assert calls == [(plugin, "new")]
