from hpc_gui import wx_shell_connections


class _Lifecycle:
    def register_cleanup(self, *_args, **_kwargs):
        pass


class _RemotePanel:
    def __init__(self, calls):
        self.calls = calls
        self._wx_remote_controls = {
            "navigate": lambda target: calls.append(("navigate", target)),
            "load": lambda: calls.append(("load",)),
        }

    def _wx_remote_set_navigation_store(self, _store):
        pass

    def _wx_remote_set_provider_filters(self, *_args):
        pass


def test_connect_uses_plugin_home_and_routes_to_terminal(monkeypatch):
    calls = []
    remote = _RemotePanel(calls)
    directories = type("Directories", (), {"_wx_dirs_rebind": lambda *_args: None})()
    selected = []
    monkeypatch.setattr(wx_shell_connections, "_update_shell_status_text", lambda *_args: None)
    monkeypatch.setattr(wx_shell_connections, "_remote_files_callbacks", lambda *_args: {
        "navigation_store": object(),
        "provider_filters": (),
        "plugin_filters": (),
    })
    monkeypatch.setattr("hpc_gui.config.storage.load_profiles", lambda: [])
    monkeypatch.setattr(
        "hpc_gui.wx_shell_events._select_embedded_page",
        lambda _state, _parent, key: selected.append(key) or True,
    )
    state = {
        "_embedded_remote_files_panel": remote,
        "_embedded_directories_panel": directories,
    }
    callbacks = wx_shell_connections._connection_callbacks(state, object(), _Lifecycle())
    session = {
        "profile": {
            "username": "alice",
            "provider_template": {
                "storage": [
                    {"id": "home", "kind": "home", "path_template": "/home/{user}"},
                    {"id": "scratch", "kind": "scratch", "path_template": "/scratch/{user}"},
                ]
            },
        }
    }

    callbacks["on_connected"](session)

    assert session["profile"]["system"]["home_dir"] == "/home/{user}"
    assert calls == [("navigate", "/home/alice"), ("load",)]
    assert selected == ["NAV-TERMINAL"]
