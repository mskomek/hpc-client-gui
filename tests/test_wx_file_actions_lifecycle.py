
pytest_plugins = ('support.test_wx_file_actions_lifecycle_shared',)
from support.test_wx_file_actions_lifecycle_shared import (
    LocalBrowserModel,
    MockRemoteFilesBackend,
    Path,
    WxRemoteDirectoryModel,
    _Dialog,
    _local,
    _remote,
    build_remote_files_panel,
    pytest,
    show_local_files,
    show_remote_files,
    threading,
    wx,
)

pytestmark = [pytest.mark.gui, pytest.mark.wx, pytest.mark.concurrency]

def test_wx_local_close_while_delete_in_flight_is_safe(wx_app, tmp_path: Path, monkeypatch):
    target = tmp_path / "remove.txt"
    target.write_text("x", encoding="utf-8")
    started = threading.Event()
    release = threading.Event()
    original = LocalBrowserModel.delete_at

    def blocked_delete(model, paths, origin=None):
        # support both signatures
        if origin is None:
            started.set()
            release.wait(2)
            return original(model, paths, model.current_path)
        started.set()
        release.wait(2)
        return original(model, paths, origin)

    monkeypatch.setattr(LocalBrowserModel, "delete_at", blocked_delete)
    monkeypatch.setattr(LocalBrowserModel, "delete", lambda self, paths: blocked_delete(self, paths, self.current_path))
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
    original = LocalBrowserModel.paste_into

    def blocked_paste_into(self, dest, clip=None, move=None):
        started.set()
        release.wait(2)
        return original(self, dest, clip, move)

    monkeypatch.setattr(LocalBrowserModel, "paste_into", blocked_paste_into)
    monkeypatch.setattr(LocalBrowserModel, "paste", lambda self: blocked_paste_into(self, self.current_path, self.clipboard, self.clipboard_move))
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
