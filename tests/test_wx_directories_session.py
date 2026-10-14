from types import SimpleNamespace

from hpc_gui.wx_directories_session import rebind_directories_storage


class _Label:
    def __init__(self):
        self.value = ""

    def SetLabel(self, value):
        self.value = value


class _Path:
    def __init__(self):
        self.value = ""

    def SetValue(self, value):
        self.value = value


class _Model:
    def __init__(self, path):
        self.current_path = path
        self.history = ["/old/provider-path"]
        self.invalidations = 0

    def invalidate(self):
        self.invalidations += 1

    def navigate(self, path):
        self.history.append(self.current_path)
        self.current_path = path


def test_rebind_navigates_and_reloads_both_connected_panes():
    models = {"scratch": _Model("/old/scratch"), "home": _Model("/old/home")}
    loads = {"scratch": 0, "home": 0}
    panes = {}
    for key, model in models.items():
        path_control = _Path()

        def navigate(target, current=model, control=path_control):
            current.navigate(target)
            control.SetValue(target)

        panes[key] = SimpleNamespace(
            _wx_remote_controls={
                "navigate": navigate,
                "load": lambda pane=key: loads.__setitem__(pane, loads[pane] + 1),
                "path": path_control,
            },
            _wx_remote_tabs=[{"back_stack": ["/old"], "forward_stack": ["/next"]}],
        )

    labels = {"scratch_label": _Label(), "home_label": _Label()}
    host = SimpleNamespace(
        _wx_dirs_models=models,
        _wx_dirs_controls={**panes, **labels},
    )
    session = {
        "session": {
            "profile": {"username": "cluster-user"},
            "cfg": {
                "username": "cluster-user",
                "system_settings": {
                    "scratch_dir": "/scratch/{user}",
                    "home_dir": "/home/{user}",
                },
            },
        }
    }

    result = rebind_directories_storage(host, session)

    assert result == {
        "scratch": "/scratch/cluster-user",
        "home": "/home/cluster-user",
    }
    assert loads == {"scratch": 1, "home": 1}
    assert models["scratch"].current_path == result["scratch"]
    assert models["home"].current_path == result["home"]
    assert models["scratch"].history == []
    assert panes["scratch"]._wx_remote_tabs[0]["back_stack"] == []
    assert panes["home"]._wx_remote_tabs[0]["forward_stack"] == []
    assert labels["scratch_label"].value == "Scratch — /scratch/cluster-user"
    assert labels["home_label"].value == "Home — /home/cluster-user"
