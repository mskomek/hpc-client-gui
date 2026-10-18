import threading
import time

import pytest

wx = pytest.importorskip("wx")

pytestmark = [pytest.mark.gui, pytest.mark.wx, pytest.mark.concurrency]

from hpc_gui.wx_remote_files import RemoteEntry, WxRemoteDirectoryModel
from hpc_gui.wx_remote_files_view import build_remote_files_panel, show_remote_files
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
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    wx.YieldIfNeeded()
    app.ProcessPendingEvents()
    app.Destroy()




def _remote(app, backend, operation):
    show_remote_files(model=WxRemoteDirectoryModel("/work"), loader=backend.iterdir_entries, operation=operation)
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls")][-1]
    _pump(app, lambda: frame._wx_remote_controls["listing"].GetItemCount() >= 1)
    return frame






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


@pytest.mark.semantic
@pytest.mark.regression
@pytest.mark.resource
def test_wx_embedded_remote_callback_after_notebook_destroy_is_ignored(wx_app, monkeypatch):
    started = threading.Event()
    release = threading.Event()
    callback_queued = threading.Event()
    pending_callbacks = []
    parent = wx.Frame(None)
    notebook = wx.Notebook(parent)

    def loader(_path):
        started.set()
        release.wait(2)
        return ()

    host = build_remote_files_panel(
        notebook,
        model=WxRemoteDirectoryModel("/work"),
        loader=loader,
        operation=lambda *_args: None,
    )
    notebook.AddPage(host, "Remote files")
    parent.Show()
    original_call_after = wx.CallAfter

    def capture_completion(callback, *args, **kwargs):
        if getattr(callback, "__name__", "") == "done":
            pending_callbacks.append((callback, args, kwargs))
            callback_queued.set()
            return None
        return original_call_after(callback, *args, **kwargs)

    monkeypatch.setattr(wx, "CallAfter", capture_completion)
    try:
        assert started.wait(2)
        release.set()
        assert callback_queued.wait(2)
        state = host._wx_remote_state

        # Destroying the parent models shell/page teardown, which does not send
        # an EVT_CLOSE event to each embedded panel.
        parent.Destroy()
        wx.SafeYield()
        assert state["closed"]
        assert len(pending_callbacks) == 1

        callback, args, kwargs = pending_callbacks[0]
        callback(*args, **kwargs)
        assert state["closed"]
    finally:
        release.set()


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




class _Dialog:
    def __init__(self, value):
        self.value = value

    def ShowModal(self):
        return wx.ID_OK

    def GetValue(self):
        return self.value

    def Destroy(self):
        pass


def test_wx_remote_listing_runs_off_gui_thread(wx_app):
    backend = MockRemoteFilesBackend()
    gui_thread = threading.get_ident()
    thread_ids = []

    def loader(path):
        thread_ids.append(threading.get_ident())
        return backend.iterdir_entries(path)

    show_remote_files(
        model=WxRemoteDirectoryModel("/work"),
        loader=loader,
        operation=backend.operation,
    )
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls")][-1]
    _pump(wx_app, lambda: frame._wx_remote_controls["listing"].GetItemCount() >= 1)
    assert thread_ids
    assert all(thread_id != gui_thread for thread_id in thread_ids)
    frame.Close(True)
