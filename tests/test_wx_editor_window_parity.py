import threading
import time

import pytest

wx = pytest.importorskip("wx")

from hpc_gui.wx_editor_windows import WxEditorWindowManager
from hpc_gui.wx_shell import _get_editor_manager


def _pump(app, predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.ProcessPendingEvents()
        if predicate():
            return
        wx.MilliSleep(2)
    app.ProcessPendingEvents()
    assert predicate()


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


def test_wx_local_edit_reuses_primary_editor(wx_app):
    manager = WxEditorWindowManager()
    primary = manager.open_primary("A.sh", "A", is_local=True)
    same = manager.open_primary("B.sh", "B", is_local=True)
    assert same is primary
    assert primary._wx_editor_model.controller.active.path == "B.sh"
    assert primary._wx_editor_controls["editor"].GetValue() == "B"
    _close(primary, wx_app)


def test_wx_local_edit_new_window_creates_independent_editor(wx_app, monkeypatch):
    manager = WxEditorWindowManager()
    primary = manager.open_primary("A.sh", "A", is_local=True)
    standalone = manager.open_new_window("B.sh", "B", is_local=True)
    assert primary is not standalone
    assert primary._wx_editor_model is not standalone._wx_editor_model
    assert primary._wx_editor_controls["editor"].GetValue() == "A"
    standalone._wx_editor_controls["editor"].SetValue("B changed")
    assert primary._wx_editor_controls["editor"].GetValue() == "A"
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.NO)
    _close(standalone, wx_app)
    assert manager.primary_frame is primary
    _close(primary, wx_app)


def test_wx_primary_editor_dirty_cancel_keeps_current_document(wx_app, monkeypatch):
    manager = WxEditorWindowManager()
    primary = manager.open_primary("A.sh", "A", is_local=True)
    primary._wx_editor_controls["editor"].SetValue("A dirty")
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.CANCEL)
    manager.open_primary("B.sh", "B", is_local=True)
    assert primary._wx_editor_model.controller.active.path == "A.sh"
    assert primary._wx_editor_controls["editor"].GetValue() == "A dirty"
    assert primary._wx_editor_model.controller.active.dirty
    _close(primary, wx_app)


def test_wx_primary_editor_dirty_discard_opens_requested_document(wx_app, monkeypatch):
    manager = WxEditorWindowManager()
    primary = manager.open_primary("A.sh", "A", is_local=True)
    primary._wx_editor_controls["editor"].SetValue("A dirty")
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.NO)
    manager.open_primary("B.sh", "B", is_local=True)
    assert primary._wx_editor_model.controller.active.path == "B.sh"
    assert primary._wx_editor_controls["editor"].GetValue() == "B"
    _close(primary, wx_app)


def test_wx_primary_editor_dirty_save_then_opens_requested_document(wx_app, monkeypatch):
    events = []
    manager = WxEditorWindowManager(save_remote=lambda path, content: events.append((path, content)))
    primary = manager.open_primary("/remote/A.sh", "A", is_local=False)
    primary._wx_editor_controls["editor"].SetValue("A dirty")
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.YES)
    manager.open_primary("/remote/B.sh", "B", is_local=False)
    _pump(wx_app, lambda: events == [("/remote/A.sh", "A dirty")])
    _pump(wx_app, lambda: primary._wx_editor_model.controller.active.path == "/remote/B.sh")
    assert primary._wx_editor_controls["editor"].GetValue() == "B"
    assert events[0][0] == "/remote/A.sh"
    _close(primary, wx_app)


def test_wx_primary_editor_failed_save_does_not_replace_document(wx_app, monkeypatch):
    manager = WxEditorWindowManager(save_remote=lambda *_args: (_ for _ in ()).throw(RuntimeError("save failed")))
    primary = manager.open_primary("/remote/A.sh", "A", is_local=False)
    primary._wx_editor_controls["editor"].SetValue("A dirty")
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.YES)
    manager.open_primary("/remote/B.sh", "B", is_local=False)
    _pump(wx_app, lambda: "save failed" in primary._wx_editor_controls["status"].GetLabel())
    assert primary._wx_editor_model.controller.active.path == "/remote/A.sh"
    assert primary._wx_editor_controls["editor"].GetValue() == "A dirty"
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.NO)
    _close(primary, wx_app)


def test_wx_edit_new_window_supports_multiple_independent_editors(wx_app, monkeypatch):
    manager = WxEditorWindowManager()
    primary = manager.open_primary("A.sh", "A", is_local=True)
    windows = [manager.open_new_window(f"{letter}.sh", letter, is_local=True) for letter in "BCD"]
    assert len(manager.standalone_frames) == 3
    assert len({id(frame) for frame in windows}) == 3
    windows[0]._wx_editor_controls["editor"].SetValue("B changed")
    assert [frame._wx_editor_model.controller.active.content for frame in windows] == ["B changed", "C", "D"]
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.NO)
    for frame in windows:
        _close(frame, wx_app)
    _close(primary, wx_app)


def test_wx_closing_standalone_editor_leaves_primary_intact(wx_app):
    manager = WxEditorWindowManager()
    primary = manager.open_primary("A.sh", "A", is_local=True)
    standalone = manager.open_new_window("B.sh", "B", is_local=True)
    _close(standalone, wx_app)
    assert manager.primary_frame is primary
    assert primary._wx_editor_controls["editor"].GetValue() == "A"
    _close(primary, wx_app)


def test_wx_primary_editor_recreated_after_close(wx_app):
    manager = WxEditorWindowManager()
    first = manager.open_primary("A.sh", "A", is_local=True)
    _close(first, wx_app)
    assert manager.primary_frame is None
    second = manager.open_primary("B.sh", "B", is_local=True)
    assert second is not first
    _close(second, wx_app)


def test_wx_primary_editor_same_file_edit_preserves_dirty_content(wx_app, monkeypatch):
    manager = WxEditorWindowManager()
    primary = manager.open_primary("A.sh", "A", is_local=True)
    primary._wx_editor_controls["editor"].SetValue("A dirty")
    manager.open_primary("A.sh", "new content", is_local=True)
    assert primary._wx_editor_controls["editor"].GetValue() == "A dirty"
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.NO)
    _close(primary, wx_app)


def test_wx_edit_new_window_allows_same_file_as_primary(wx_app):
    manager = WxEditorWindowManager()
    primary = manager.open_primary("A.sh", "A", is_local=True)
    standalone = manager.open_new_window("A.sh", "A copy", is_local=True)
    assert primary is not standalone
    assert standalone._wx_editor_model is not primary._wx_editor_model
    _close(standalone, wx_app)
    _close(primary, wx_app)


def test_wx_editor_window_manager_repeated_open_close_does_not_leak_frames(wx_app):
    manager = WxEditorWindowManager()
    for index in range(25):
        primary = manager.open_primary(f"P{index}.sh", "P", is_local=True)
        standalone = manager.open_new_window(f"S{index}.sh", "S", is_local=True)
        _close(standalone, wx_app)
        _close(primary, wx_app)
    assert not [window for window in wx.GetTopLevelWindows() if window and window.GetTitle().endswith(".sh")]


def test_wx_primary_editor_pending_save_replace_cannot_overwrite_newer_edit(wx_app, monkeypatch):
    started, release = threading.Event(), threading.Event()

    def save_remote(_path, _content):
        started.set()
        release.wait(2)

    manager = WxEditorWindowManager(save_remote=save_remote)
    primary = manager.open_primary("/remote/A.sh", "A", is_local=False)
    primary._wx_editor_controls["editor"].SetValue("A dirty")
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.YES)
    manager.open_primary("/remote/B.sh", "B", is_local=False)
    assert started.wait(1)
    manager.open_primary("/remote/C.sh", "C", is_local=False)
    release.set()
    _pump(wx_app, lambda: primary._wx_editor_model.controller.active.path == "/remote/C.sh")
    assert primary._wx_editor_controls["editor"].GetValue() == "C"
    _close(primary, wx_app)


def test_wx_shell_reuses_one_editor_manager_for_local_and_remote_views():
    class Lifecycle:
        def __init__(self):
            self.cleanups = []

        def register_cleanup(self, callback):
            self.cleanups.append(callback)

    state = {}
    lifecycle = Lifecycle()
    first = _get_editor_manager(state, None, lifecycle)
    second = _get_editor_manager(state, None, lifecycle, save_remote=lambda *_args: None)
    assert second is first
    assert len(lifecycle.cleanups) == 1
    first.close_all()
