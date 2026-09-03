import threading
import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.wx_editor_windows import WxEditorWindowManager
from hpc_gui.wx_remote_files import RemoteEntry
from hpc_gui.wx_remote_files_view import show_remote_files


def _pump(app, predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if predicate():
            return
        wx.MilliSleep(2)
    app.ProcessPendingEvents()
    assert predicate()


def _activate(frame, index):
    listing = frame._wx_remote_controls["listing"]
    listing.Select(index)
    event = wx.ListEvent(wx.wxEVT_LIST_ITEM_ACTIVATED, listing.GetId())
    event.SetIndex(index)
    listing.ProcessEvent(event)


def _close(frame, app):
    frame.Close()
    app.ProcessPendingEvents()
    wx.Yield()


@pytest.fixture
def wx_app():
    app = wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()


def _browser(manager, read_text):
    def editor(path, content="", request_id=None):
        manager.open_primary(path, content, is_local=False, request_id=request_id)

    editor._wx_request_aware = True
    editor._wx_request_started = manager.begin_primary_request

    show_remote_files(
            loader=lambda _path: (RemoteEntry("/remote/A.sh", size=1), RemoteEntry("/remote/B.sh", size=1)),
        read_text=read_text,
        open_editor=editor,
        open_editor_new_window=lambda path, content="": manager.open_new_window(path, content),
    )
    frame = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_remote_controls")][-1]
    return frame


def test_wx_remote_browser_edit_opens_visible_primary_editor(wx_app):
    gui_thread = threading.get_ident()
    reads = []
    manager = WxEditorWindowManager()

    def read(path):
        reads.append(threading.get_ident())
        return f"content-{path.rsplit('/', 1)[-1]}"

    browser = _browser(manager, read)
    _pump(wx_app, lambda: browser._wx_remote_controls["listing"].GetItemCount() == 2)
    _activate(browser, 0)
    _pump(wx_app, lambda: manager.primary_frame is not None)
    assert manager.primary_frame._wx_editor_controls["editor"].GetValue() == "content-A.sh"
    assert reads and reads[0] != gui_thread
    _close(browser, wx_app)
    _close(manager.primary_frame, wx_app)


def test_wx_remote_browser_edit_reuses_primary_editor(wx_app):
    manager = WxEditorWindowManager()
    browser = _browser(manager, lambda path: f"content-{path.rsplit('/', 1)[-1]}")
    _pump(wx_app, lambda: browser._wx_remote_controls["listing"].GetItemCount() == 2)
    _activate(browser, 0)
    _pump(wx_app, lambda: manager.primary_frame is not None)
    primary = manager.primary_frame
    _activate(browser, 1)
    _pump(wx_app, lambda: primary._wx_editor_model.controller.active.path == "/remote/B.sh")
    assert manager.primary_frame is primary
    assert primary._wx_editor_controls["editor"].GetValue() == "content-B.sh"
    _close(browser, wx_app)
    _close(primary, wx_app)


def test_wx_remote_browser_edit_new_window_creates_visible_independent_editor(wx_app):
    manager = WxEditorWindowManager()
    browser = _browser(manager, lambda path: f"content-{path.rsplit('/', 1)[-1]}")
    _pump(wx_app, lambda: browser._wx_remote_controls["listing"].GetItemCount() == 2)
    _activate(browser, 0)
    _pump(wx_app, lambda: manager.primary_frame is not None)
    primary = manager.primary_frame
    browser._wx_remote_run_action("edit_new_window", ("/remote/B.sh",))
    _pump(wx_app, lambda: len(manager.standalone_frames) == 1)
    standalone = next(iter(manager.standalone_frames))
    assert standalone is not primary
    assert standalone._wx_editor_controls["editor"].GetValue() == "content-B.sh"
    _close(browser, wx_app)
    _close(standalone, wx_app)
    _close(primary, wx_app)


def test_wx_remote_browser_read_failure_preserves_existing_primary_editor(wx_app, monkeypatch):
    manager = WxEditorWindowManager()
    calls = []

    def read(path):
        if path.endswith("B.sh"):
            raise RuntimeError("read failed")
        return "content-A"

    browser = _browser(manager, read)
    _pump(wx_app, lambda: browser._wx_remote_controls["listing"].GetItemCount() == 2)
    _activate(browser, 0)
    _pump(wx_app, lambda: manager.primary_frame is not None)
    primary = manager.primary_frame
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: calls.append(True) or wx.OK)
    _activate(browser, 1)
    _pump(wx_app, lambda: calls)
    assert manager.primary_frame is primary
    assert primary._wx_editor_model.controller.active.path == "/remote/A.sh"
    _close(browser, wx_app)
    _close(primary, wx_app)


def test_wx_remote_browser_new_window_read_failure_creates_no_editor(wx_app, monkeypatch):
    manager = WxEditorWindowManager()
    browser = _browser(manager, lambda _path: (_ for _ in ()).throw(RuntimeError("read failed")))
    _pump(wx_app, lambda: browser._wx_remote_controls["listing"].GetItemCount() == 2)
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.OK)
    browser._wx_remote_run_action("edit_new_window", ("/remote/B.sh",))
    _pump(wx_app, lambda: not browser._wx_remote_state["busy"])
    assert not manager.standalone_frames
    _close(browser, wx_app)


def test_wx_remote_browser_close_during_editor_read_discards_result(wx_app):
    started, release = threading.Event(), threading.Event()
    manager = WxEditorWindowManager()

    def read(_path):
        started.set()
        release.wait(2)
        return "late"

    browser = _browser(manager, read)
    _pump(wx_app, lambda: browser._wx_remote_controls["listing"].GetItemCount() == 2)
    _activate(browser, 0)
    assert started.wait(1)
    _close(browser, wx_app)
    release.set()
    wx_app.ProcessPendingEvents()
    assert manager.primary_frame is None


def test_wx_remote_browser_stale_read_does_not_overwrite_newer_edit(wx_app):
    a_started, release_a = threading.Event(), threading.Event()
    manager = WxEditorWindowManager()

    def read(path):
        if path.endswith("A.sh"):
            a_started.set()
            release_a.wait(2)
            return "content-A-late"
        return "content-B"

    browser = _browser(manager, read)
    _pump(wx_app, lambda: browser._wx_remote_controls["listing"].GetItemCount() == 2)
    _activate(browser, 0)
    assert a_started.wait(1)
    _activate(browser, 1)
    _pump(wx_app, lambda: manager.primary_frame is not None and manager.primary_model.controller.active.path == "/remote/B.sh")
    release_a.set()
    _pump(wx_app, lambda: manager.primary_frame._wx_editor_controls["editor"].GetValue() == "content-B")
    assert manager.primary_model.controller.active.path == "/remote/B.sh"
    _close(browser, wx_app)
    _close(manager.primary_frame, wx_app)
