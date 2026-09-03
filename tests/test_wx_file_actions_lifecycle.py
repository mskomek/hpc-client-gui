import threading
import time
from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.wx_local_files import LocalBrowserModel, show_local_files
from hpc_gui.wx_remote_files import WxRemoteDirectoryModel
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


class _Dialog:
    def __init__(self, value):
        self.value = value

    def ShowModal(self):
        return wx.ID_OK

    def GetValue(self):
        return self.value

    def Destroy(self):
        pass
