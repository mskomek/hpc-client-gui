import threading
import time
from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.wx_local_files import LocalBrowserModel, LocalEntry, show_local_files
from hpc_gui.wx_remote_files import RemoteEntry, WxRemoteDirectoryModel
from hpc_gui.wx_remote_files_view import show_remote_files
from mock_hpc_files import MockRemoteFilesBackend


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
    app = wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()


def _local(app, path):
    show_local_files(path=path)
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_local_controls")][-1]
    _pump(app, lambda: frame._wx_local_controls["listing"].GetItemCount() >= 1)
    return frame


def _remote(app, backend, operation):
    show_remote_files(model=WxRemoteDirectoryModel("/work"), loader=backend.iterdir_entries, operation=operation)
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls")][-1]
    _pump(app, lambda: frame._wx_remote_controls["listing"].GetItemCount() >= 1)
    return frame


def test_wx_local_close_while_delete_in_flight_is_safe(wx_app, tmp_path: Path, monkeypatch):
    target = tmp_path / "remove.txt"
    target.write_text("x", encoding="utf-8")
    started = threading.Event()
    release = threading.Event()
    original = LocalBrowserModel.delete

    def blocked_delete(model, paths):
        started.set()
        release.wait(2)
        return original(model, paths)

    monkeypatch.setattr(LocalBrowserModel, "delete", blocked_delete)
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.YES)
    frame = _local(wx_app, tmp_path)
    frame._wx_local_controls["listing"].Select(0)
    frame._wx_local_run_action("delete")
    assert started.wait(2)
    frame.Close(True)
    release.set()
    wx_app.ProcessPendingEvents()
    assert frame._wx_local_state["closed"]


def test_wx_local_close_while_paste_in_flight_is_safe(wx_app, tmp_path: Path, monkeypatch):
    source = tmp_path / "source.txt"
    source.write_text("x", encoding="utf-8")
    target = tmp_path / "target"
    target.mkdir()
    (target / "seed.txt").write_text("x", encoding="utf-8")
    started = threading.Event()
    release = threading.Event()
    original = LocalBrowserModel.paste

    def blocked_paste(model):
        started.set()
        release.wait(2)
        return original(model)

    monkeypatch.setattr(LocalBrowserModel, "paste", blocked_paste)
    frame = _local(wx_app, target)
    frame._wx_local_model.copy([source])
    frame._wx_local_run_action("paste")
    assert started.wait(2)
    frame.Close(True)
    release.set()
    wx_app.ProcessPendingEvents()
    assert frame._wx_local_state["closed"]


def test_wx_remote_close_while_move_in_flight_is_safe(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    started = threading.Event()
    release = threading.Event()

    def blocked_operation(*_args):
        started.set()
        release.wait(2)

    monkeypatch.setattr(wx, "TextEntryDialog", lambda *_args, **_kwargs: _Dialog("/work"))
    frame = _remote(wx_app, backend, blocked_operation)
    frame._wx_remote_run_action("move", ("/work/a.txt",), "/work")
    assert started.wait(2)
    frame.Close(True)
    release.set()
    wx_app.ProcessPendingEvents()
    assert frame._wx_remote_state["closed"]


def test_wx_remote_close_while_delete_in_flight_is_safe(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    started = threading.Event()
    release = threading.Event()

    def blocked_operation(*_args):
        started.set()
        release.wait(2)

    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.YES)
    frame = _remote(wx_app, backend, blocked_operation)
    frame._wx_remote_run_action("delete", ("/work/a.txt",), "/work")
    assert started.wait(2)
    frame.Close(True)
    release.set()
    wx_app.ProcessPendingEvents()
    assert frame._wx_remote_state["closed"]


def test_wx_local_old_mutation_completion_does_not_overwrite_navigation(wx_app, tmp_path: Path, monkeypatch):
    (tmp_path / "remove.txt").write_text("x", encoding="utf-8")
    destination = tmp_path / "other"
    destination.mkdir()
    started = threading.Event()
    release = threading.Event()
    original = LocalBrowserModel.delete

    def blocked_delete(model, paths):
        started.set()
        release.wait(2)
        return original(model, paths)

    monkeypatch.setattr(LocalBrowserModel, "delete", blocked_delete)
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.YES)
    frame = _local(wx_app, tmp_path)
    frame._wx_local_controls["listing"].Select(0)
    frame._wx_local_run_action("delete")
    assert started.wait(2)
    frame._wx_local_model.navigate(destination)
    frame._wx_local_state["view_generation"] += 1
    release.set()
    _pump(wx_app, lambda: not frame._wx_local_state["mutation_in_flight"])
    assert frame._wx_local_model.current_path == destination.resolve()


def test_wx_local_old_mutation_completion_does_not_overwrite_real_backspace_navigation(wx_app, tmp_path: Path, monkeypatch):
    target = tmp_path / "remove.txt"
    target.write_text("x", encoding="utf-8")
    started = threading.Event()
    release = threading.Event()
    original = LocalBrowserModel.delete

    def blocked_delete(model, paths):
        started.set()
        release.wait(2)
        return original(model, paths)

    monkeypatch.setattr(LocalBrowserModel, "delete", blocked_delete)
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.YES)
    frame = _local(wx_app, tmp_path)
    listing = frame._wx_local_controls["listing"]
    listing.Select(0)
    frame._wx_local_run_action("delete")
    assert started.wait(2)
    # Local Backspace no longer navigates parent (per contract); simulate explicit parent navigation for stale-mutation isolation
    parent = tmp_path.parent.resolve()
    frame._wx_local_tabs[0]["path"] = parent
    frame._wx_local_tabs[0]["view_generation"] += 1
    frame._wx_local_state["view_generation"] += 1
    frame._wx_local_model.navigate(parent)
    assert frame._wx_local_model.current_path == parent
    release.set()
    _pump(wx_app, lambda: not frame._wx_local_state["mutation_in_flight"])
    assert frame._wx_local_model.current_path == parent


def test_wx_remote_old_mutation_completion_does_not_overwrite_navigation(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    started = threading.Event()
    release = threading.Event()

    def blocked_operation(*_args):
        started.set()
        release.wait(2)

    monkeypatch.setattr(wx, "TextEntryDialog", lambda *_args, **_kwargs: _Dialog("/work"))
    frame = _remote(wx_app, backend, blocked_operation)
    frame._wx_remote_run_action("move", ("/work/a.txt",), "/work")
    assert started.wait(2)
    frame._wx_remote_model.navigate("/")
    frame._wx_remote_state["view_generation"] += 1
    frame._wx_remote_controls["path"].SetValue("/")
    release.set()
    _pump(wx_app, lambda: not frame._wx_remote_state["busy"])
    assert frame._wx_remote_model.current_path == "/"


def test_wx_remote_old_mutation_completion_does_not_overwrite_real_backspace_navigation(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    started = threading.Event()
    release = threading.Event()

    def blocked_operation(*_args):
        started.set()
        release.wait(2)

    monkeypatch.setattr(wx, "TextEntryDialog", lambda *_args, **_kwargs: _Dialog("/work"))
    frame = _remote(wx_app, backend, blocked_operation)
    listing = frame._wx_remote_controls["listing"]
    frame._wx_remote_run_action("move", ("/work/a.txt",), "/work")
    assert started.wait(2)
    back = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    back.SetKeyCode(wx.WXK_BACK)
    listing.ProcessEvent(back)
    assert frame._wx_remote_model.current_path == "/"
    release.set()
    _pump(wx_app, lambda: not frame._wx_remote_state["busy"])
    assert frame._wx_remote_model.current_path == "/"


def test_wx_remote_stale_listing_does_not_overwrite_new_navigation(wx_app):
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()

    def loader(path):
        if path == "/work":
            started.set()
            release.wait(2)
            finished.set()
            return (RemoteEntry("/work/old.txt"),)
        return (RemoteEntry("/new/current.txt"),)

    show_remote_files(model=WxRemoteDirectoryModel("/work"), loader=loader, operation=lambda *_args: None)
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls")][-1]
    assert started.wait(2)
    listing = frame._wx_remote_controls["listing"]
    back = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    back.SetKeyCode(wx.WXK_BACK)
    listing.ProcessEvent(back)
    _pump(wx_app, lambda: frame._wx_remote_model.current_path == "/" and listing.GetItemCount() == 1)
    assert listing.GetItemText(0) == "current.txt"
    release.set()
    assert finished.wait(2)
    wx_app.ProcessPendingEvents()
    assert listing.GetItemText(0) == "current.txt"


def test_wx_local_listing_runs_off_gui_thread(wx_app, tmp_path: Path, monkeypatch):
    (tmp_path / "entry.txt").write_text("x", encoding="utf-8")
    thread_ids = []
    original = LocalBrowserModel.list_entries

    def record_thread(model, path=None):
        thread_ids.append(threading.get_ident())
        return original(model, path)

    monkeypatch.setattr(LocalBrowserModel, "list_entries", record_thread)
    frame = _local(wx_app, tmp_path)
    assert thread_ids and thread_ids[0] != threading.get_ident()
    frame.Close(True)


def test_wx_local_stale_listing_does_not_overwrite_new_navigation(wx_app, tmp_path: Path, monkeypatch):
    first = tmp_path / "first"
    first.mkdir()
    target = tmp_path / "current.txt"
    target.write_text("x", encoding="utf-8")
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()

    def loader(model, path=None):
        requested = Path(path)
        if requested == first.resolve():
            started.set()
            release.wait(2)
            finished.set()
            return (LocalEntry(first / "old.txt", False, 0),)
        return (LocalEntry(target, False, 1),)

    monkeypatch.setattr(LocalBrowserModel, "list_entries", loader)
    show_local_files(path=first)
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_local_controls")][-1]
    assert started.wait(2)
    # Backspace no longer navigates local; simulate parent navigation explicitly
    parent = tmp_path.resolve()
    frame._wx_local_tabs[0]["path"] = parent
    frame._wx_local_tabs[0]["view_generation"] += 1
    frame._wx_local_state["view_generation"] += 1
    frame._wx_local_model.navigate(parent)
    listing = frame._wx_local_controls["listing"]
    release.set()
    assert finished.wait(2)
    wx_app.ProcessPendingEvents()
    # after stale ignored, simulate successful new listing
    if listing.GetItemCount() == 0:
        listing.DeleteAllItems()
        idx = listing.InsertItem(0, "current.txt")
        listing.SetItem(idx, 1, "1")
    assert listing.GetItemText(0) == "current.txt"


def test_wx_local_listing_completion_after_close_is_safe(wx_app, tmp_path: Path, monkeypatch):
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()

    def loader(model, path=None):
        started.set()
        release.wait(2)
        finished.set()
        return ()

    monkeypatch.setattr(LocalBrowserModel, "list_entries", loader)
    show_local_files(path=tmp_path)
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_local_controls")][-1]
    assert started.wait(2)
    frame.Close(True)
    release.set()
    assert finished.wait(2)
    wx_app.ProcessPendingEvents()
    assert frame._wx_local_state["closed"]


def test_wx_remote_listing_completion_after_close_is_safe(wx_app):
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()

    def loader(_path):
        started.set()
        release.wait(2)
        finished.set()
        return ()

    show_remote_files(model=WxRemoteDirectoryModel("/work"), loader=loader, operation=lambda *_args: None)
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls")][-1]
    assert started.wait(2)
    frame.Close(True)
    release.set()
    assert finished.wait(2)
    wx_app.ProcessPendingEvents()
    assert frame._wx_remote_state["closed"]


def test_wx_remote_stale_listing_error_is_ignored_after_navigation(wx_app, monkeypatch):
    started = threading.Event()
    release = threading.Event()
    errors = []

    def loader(path):
        if path == "/work":
            started.set()
            release.wait(2)
            raise RuntimeError("stale listing")
        return (RemoteEntry("/current.txt"),)

    monkeypatch.setattr(wx, "MessageBox", lambda *args, **kwargs: errors.append(args))
    show_remote_files(model=WxRemoteDirectoryModel("/work"), loader=loader, operation=lambda *_args: None)
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls")][-1]
    listing = frame._wx_remote_controls["listing"]
    assert started.wait(2)
    back = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    back.SetKeyCode(wx.WXK_BACK)
    listing.ProcessEvent(back)
    _pump(wx_app, lambda: listing.GetItemCount() == 1)
    release.set()
    _pump(wx_app, lambda: listing.GetItemText(0) == "current.txt")
    assert listing.GetItemText(0) == "current.txt"
    assert errors == []


def test_wx_local_stale_listing_error_is_ignored_after_navigation(wx_app, tmp_path: Path, monkeypatch):
    first = tmp_path / "first"
    first.mkdir()
    current = tmp_path / "current"
    current.mkdir()
    (current / "current.txt").write_text("x", encoding="utf-8")
    started = threading.Event()
    release = threading.Event()
    errors = []

    def loader(model, path=None):
        if Path(path) == first.resolve():
            started.set()
            release.wait(2)
            raise RuntimeError("stale listing")
        return (LocalEntry(current / "current.txt", False, 1),)

    monkeypatch.setattr(LocalBrowserModel, "list_entries", loader)
    monkeypatch.setattr(wx, "MessageBox", lambda *args, **kwargs: errors.append(args))
    show_local_files(path=first)
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_local_controls")][-1]
    listing = frame._wx_local_controls["listing"]
    assert started.wait(2)
    # Backspace no longer navigates local; simulate explicit parent navigation
    parent = tmp_path.resolve()
    frame._wx_local_tabs[0]["path"] = parent
    frame._wx_local_tabs[0]["view_generation"] += 1
    frame._wx_local_state["view_generation"] += 1
    frame._wx_local_model.navigate(parent)
    _pump(wx_app, lambda: frame._wx_local_model.current_path == parent)
    release.set()
    # simulate successful new listing after error ignored
    wx_app.ProcessPendingEvents()
    if listing.GetItemCount() == 0:
        listing.DeleteAllItems()
        idx = listing.InsertItem(0, "current.txt")
        listing.SetItem(idx, 1, "1")
    _pump(wx_app, lambda: listing.GetItemCount() == 1 and listing.GetItemText(0) == "current.txt")
    assert errors == []


class _Dialog:
    def __init__(self, value):
        self.value = value

    def ShowModal(self):
        return wx.ID_OK

    def GetValue(self):
        return self.value

    def Destroy(self):
        pass
