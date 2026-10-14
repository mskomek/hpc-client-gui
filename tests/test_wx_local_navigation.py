from pathlib import Path
from types import SimpleNamespace

from hpc_gui.services.local_navigation_store import LocalNavigationStore
from hpc_gui.wx_local_files_navigation import _navigate_local_browser


class _Control:
    def __init__(self):
        self.value = ""
        self.enabled = None

    def SetValue(self, value):
        self.value = value

    def Enable(self, enabled):
        self.enabled = enabled


class _Notebook:
    def __init__(self):
        self.labels = []

    def GetSelection(self):
        return 0

    def SetPageText(self, index, value):
        self.labels.append((index, value))


class _LocalModel:
    def __init__(self, path):
        self.current_path = Path(path)
        self.active_tab = 0
        self._history = []
        self._forward = []

    def navigate(self, target):
        target = Path(target)
        if target != self.current_path:
            self._history.append(self.current_path)
            self._forward.clear()
        self.current_path = target

    def can_go_back(self):
        return bool(self._history)

    def can_go_forward(self):
        return bool(self._forward)


def test_local_navigation_updates_the_active_tab_and_refreshes_listing(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    model = _LocalModel(source)
    notebook = _Notebook()
    path_control = _Control()
    refreshes = []
    tab = {"path": source, "view_generation": 0}
    browser = SimpleNamespace(
        _wx_local_model=model,
        _wx_local_notebook=notebook,
        _wx_local_tabs=[tab],
        _wx_local_state={"view_generation": 0},
        _wx_local_controls={
            "path": path_control,
            "btn_back": _Control(),
            "btn_forward": _Control(),
        },
        _wx_local_refresh=lambda: refreshes.append(model.current_path),
    )

    _navigate_local_browser(browser, target)

    assert model.current_path == target
    assert tab["path"] == target
    assert path_control.value == str(target)
    assert notebook.labels == [(0, "target")]
    assert browser._wx_local_controls["btn_back"].enabled is True
    assert refreshes == [target]


def test_local_navigation_store_persists_favorites_and_deduplicated_history(tmp_path):
    favorite = tmp_path / "favorite"
    recent = tmp_path / "recent"
    favorite.mkdir()
    recent.mkdir()
    path = tmp_path / "navigation.json"
    store = LocalNavigationStore(path)

    store.add_favorite(favorite)
    store.add_favorite(favorite)
    store.record_visit(favorite)
    store.record_visit(recent)
    store.record_visit(favorite)

    reopened = LocalNavigationStore(path)
    assert reopened.favorites() == [{"path": str(favorite.resolve()), "label": "favorite"}]
    assert [entry["path"] for entry in reopened.history()] == [
        str(favorite.resolve()),
        str(recent.resolve()),
    ]
    reopened.remove_favorite(favorite)
    reopened.clear_history()
    assert reopened.favorites() == []
    assert reopened.history() == []
