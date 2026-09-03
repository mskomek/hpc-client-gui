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
    app = wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        if window:
            window.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()


def _frame(app, backend, operation=None):
    show_remote_files(
        model=WxRemoteDirectoryModel("/work"),
        loader=backend.iterdir_entries,
        operation=operation or backend.operation,
    )
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_remote_controls")][-1]
    _pump(app, lambda: frame._wx_remote_controls["listing"].GetItemCount() >= 1)
    return frame


def _key(code):
    event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(code)
    event.SetControlDown(True)
    return event


def test_wx_remote_ctrl_z_undoes_last_successful_move(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    frame = _frame(wx_app, backend)
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *_args, **_kwargs: _Dialog("/"))
    frame._wx_remote_run_action("move", ("/work/a.txt",), "/")
    _pump(wx_app, lambda: ("move", "/work/a.txt", "/a.txt") in backend.calls and not frame._wx_remote_state["busy"])
    frame._wx_remote_controls["listing"].ProcessEvent(_key(ord("Z")))
    _pump(wx_app, lambda: ("move", "/a.txt", "/work/a.txt") in backend.calls and not frame._wx_remote_state["busy"])
    assert "/work/a.txt" in backend.entries


def test_wx_remote_ctrl_z_is_noop_without_move_history(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _frame(wx_app, backend)
    before = list(backend.calls)
    frame._wx_remote_controls["listing"].ProcessEvent(_key(ord("Z")))
    wx_app.ProcessPendingEvents()
    assert backend.calls == before


def test_wx_remote_ctrl_z_does_not_undo_copy(wx_app):
    backend = MockRemoteFilesBackend()
    frame = _frame(wx_app, backend)
    frame._wx_remote_run_action("copy", ("/work/a.txt",), "/")
    frame._wx_remote_controls["listing"].ProcessEvent(_key(ord("Z")))
    wx_app.ProcessPendingEvents()
    assert not any(call[0] == "move" for call in backend.calls)


def test_wx_remote_multi_move_ctrl_z_restores_original_paths(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    frame = _frame(wx_app, backend)
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *_args, **_kwargs: _Dialog("/"))
    frame._wx_remote_run_action("move", ("/work/a.txt", "/work/b.txt"), "/")
    _pump(wx_app, lambda: not frame._wx_remote_state["busy"])
    frame._wx_remote_controls["listing"].ProcessEvent(_key(ord("Z")))
    _pump(wx_app, lambda: not frame._wx_remote_state["busy"] and "/work/a.txt" in backend.entries and "/work/b.txt" in backend.entries)
    assert "/a.txt" not in backend.entries and "/b.txt" not in backend.entries


def test_wx_remote_failed_move_is_not_registered_for_undo(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *_args, **_kwargs: _Dialog("/"))
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.OK)

    def fail(_action, _paths, _destination=""):
        raise RuntimeError("move failed")

    frame = _frame(wx_app, backend, operation=fail)
    frame._wx_remote_run_action("move", ("/work/a.txt",), "/")
    _pump(wx_app, lambda: not frame._wx_remote_state["busy"])
    assert not any(call[0] == "move" for call in backend.calls)
    frame._wx_remote_controls["listing"].ProcessEvent(_key(ord("Z")))
    _pump(wx_app, lambda: not frame._wx_remote_state["busy"])
    assert not any(call[0] == "move" for call in backend.calls)


def test_wx_remote_ctrl_z_failure_preserves_consistent_history(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    calls = []
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *_args, **_kwargs: _Dialog("/"))
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.OK)

    def operation(action, paths, destination=""):
        calls.append((action, tuple(paths), destination))
        if len(calls) > 1:
            raise RuntimeError("undo failed")
        backend.operation(action, paths, destination)

    frame = _frame(wx_app, backend, operation=operation)
    frame._wx_remote_run_action("move", ("/work/a.txt",), "/")
    _pump(wx_app, lambda: not frame._wx_remote_state["busy"])
    assert "/a.txt" in backend.entries
    frame._wx_remote_controls["listing"].ProcessEvent(_key(ord("Z")))
    _pump(wx_app, lambda: not frame._wx_remote_state["busy"])
    assert "/a.txt" in backend.entries
    frame._wx_remote_controls["listing"].ProcessEvent(_key(ord("Z")))
    _pump(wx_app, lambda: not frame._wx_remote_state["busy"])
    assert "/a.txt" in backend.entries


class _Dialog:
    def __init__(self, value):
        self.value = value

    def ShowModal(self):
        return wx.ID_OK

    def GetValue(self):
        return self.value

    def Destroy(self):
        pass
