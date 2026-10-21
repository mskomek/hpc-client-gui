import time

import pytest

wx = pytest.importorskip("wx")

from mock_hpc_files import MockRemoteFilesBackend

from hpc_gui.core.i18n import load_language

from hpc_gui.wx_remote_files import WxRemoteDirectoryModel

from hpc_gui.wx_remote_files_view import show_remote_files

def _pump(app, predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if predicate():
            return
        wx.MilliSleep(5)
    app.ProcessPendingEvents()
    assert predicate()

@pytest.fixture
def wx_app():
    load_language("en")
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    yield app
    for window in list(wx.GetTopLevelWindows()):
        if window and not window.IsBeingDeleted():
            window.Close()
    for _ in range(3):
        app.ProcessPendingEvents()
        wx.Yield()
    for window in list(wx.GetTopLevelWindows()):
        if window and not window.IsBeingDeleted():
            window.Destroy()
    app.ProcessPendingEvents()
    wx.Yield()
    assert not wx.GetTopLevelWindows(), "wx top-level windows survived fixture teardown"
    app.Destroy()

def test_wx_remote_navigation_sort_and_provider_filter_are_visible(wx_app):
    backend = MockRemoteFilesBackend()
    backend.entries.update({
        "/work/Folder A": True, "/work/Folder B": True,
        "/work/z.txt": False, "/work/run.log": False,
        "/work/sub": True, "/work/sub/child.txt": False,
    })
    show_remote_files(
        model=WxRemoteDirectoryModel("/work"), loader=backend.iterdir_entries,
        operation=backend.operation,
        provider_filters=[{"id": "logs", "labels": {"en": "Logs", "tr": "Günlükler"}, "suffixes": [".log"], "order": 100}],
    )
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls")][-1]
    _pump(wx_app, lambda: frame._wx_remote_controls["listing"].GetItemCount() >= 1)
    controls = frame._wx_remote_controls
    listing = controls["listing"]
    for _ in range(2):
        event = wx.ListEvent(wx.wxEVT_LIST_COL_CLICK, listing.GetId())
        event.SetColumn(0)
        event.SetEventObject(listing)
        listing.GetEventHandler().ProcessEvent(event)
    names = [
        listing.GetItemText(index)
        for index in range(listing.GetItemCount())
        if listing.GetItemText(index) != ".."
    ]
    assert names[:3] == ["sub", "Folder B", "Folder A"]
    assert set(names[3:]) == {"z.txt", "run.log", "a.txt", "b.txt"}

    tab = frame._wx_remote_tabs[0]
    filter_nb = tab["filter_notebook"]
    assert "Logs" in [filter_nb.GetPageText(index) for index in range(filter_nb.GetPageCount())]
    filter_nb.SetSelection(tab["filter_ids"].index("logs"))
    wx_app.ProcessPendingEvents()
    assert [listing.GetItemText(index) for index in range(listing.GetItemCount())] == ["..", "run.log"]

    controls["navigate"]("/work/sub")
    controls["load"]()
    _pump(wx_app, lambda: controls["path"].GetValue() == "/work/sub")
    controls["btn_back"].ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, controls["btn_back"].GetId()))
    _pump(wx_app, lambda: controls["path"].GetValue() == "/work")
    controls["btn_forward"].ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, controls["btn_forward"].GetId()))
    _pump(wx_app, lambda: controls["path"].GetValue() == "/work/sub")

def test_wx_remote_favorite_selected_file_targets_file_path(wx_app):
    class Store:
        def __init__(self):
            self.items = []

        def favorites(self):
            return list(self.items)

        def toggle_favorite(self, path, kind):
            self.items.append({"path": path, "kind": kind, "label": path.rsplit("/", 1)[-1]})

    store = Store()
    backend = MockRemoteFilesBackend()
    show_remote_files(
        model=WxRemoteDirectoryModel("/work"), loader=backend.iterdir_entries,
        operation=backend.operation, navigation_store=store,
    )
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls")][-1]
    _pump(wx_app, lambda: frame._wx_remote_controls["listing"].GetItemCount() >= 1)
    frame._wx_remote_run_action("favorite", ("/work/a.txt",), "/work")
    assert store.items == [{"path": "/work/a.txt", "kind": "file", "label": "a.txt"}]

def test_wx_remote_submit_slurm_uses_selected_remote_path(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    submitted = []
    messages = []
    frame = show_remote_files(
        model=WxRemoteDirectoryModel("/work"), loader=backend.iterdir_entries,
        operation=backend.operation,
        submit_slurm=lambda path: submitted.append(path) or "Submitted batch job 77",
    )
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls")][-1]
    _pump(wx_app, lambda: frame._wx_remote_controls["listing"].GetItemCount() >= 1)
    monkeypatch.setattr(wx, "MessageBox", lambda message, *_args, **_kwargs: messages.append(message) or wx.OK)
    frame._wx_remote_run_action("submit_slurm", ("/work/job.sbatch",), "/work")
    _pump(wx_app, lambda: not frame._wx_remote_state["busy"])
    assert submitted == ["/work/job.sbatch"]
    assert messages == ["Submitted batch job 77"]
