from support.test_wx_file_transfer_integration_shared import (
    TransferItem,
    _BlockingFiles,
    _FailingFiles,
    _Files,
    _Lifecycle,
    _ResumableFiles,
    _start_file_transfers,
    pytest,
    time,
)

pytestmark = pytest.mark.wx

@pytest.mark.integration
@pytest.mark.concurrency
def test_wx_file_transfer_uses_operation_session_snapshot():
    files_a = _BlockingFiles()
    files_b = _Files()
    state = {"session": {"files": files_a}}
    controller = _start_file_transfers(
        state,
        _Lifecycle(),
        [TransferItem("upload", "a.txt", "/a.txt")],
        files_backend=files_a,
    )
    assert files_a.started.wait(2)
    state["session"] = {"files": files_b}
    files_a.release.set()
    assert controller.engine.wait(2)
    assert files_a.calls == [("upload", "a.txt", "/a.txt")]
    assert files_b.calls == []
    next_controller = _start_file_transfers(
        state,
        _Lifecycle(),
        [TransferItem("upload", "b.txt", "/b.txt")],
    )
    assert next_controller.engine.wait(2)
    assert files_b.calls == [("upload", "b.txt", "/b.txt")]

@pytest.mark.integration
def test_file_context_transfer_uses_transfer_session_boundary():
    files = _Files()
    lifecycle = _Lifecycle()
    state = {"session": {"files": files}}
    controller = _start_file_transfers(state, lifecycle, [TransferItem("upload", "iş sonuç.txt", "/work/iş sonuç.txt")])
    assert controller.engine.wait(2)
    assert files.calls == [("upload", "iş sonuç.txt", "/work/iş sonuç.txt")]
    assert lifecycle.cleanups

@pytest.mark.integration
@pytest.mark.resource
def test_wx_file_transfer_session_removed_after_success():
    files = _Files()
    state = {"session": {"files": files}}
    controller = _start_file_transfers(state, _Lifecycle(), [TransferItem("upload", "a.txt", "/a.txt")])
    assert controller.engine.wait(2)
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline and state.get("transfer_sessions"):
        time.sleep(0.01)
    assert state["transfer_sessions"] == set()

@pytest.mark.integration
@pytest.mark.resource
def test_wx_file_transfer_session_removed_after_failure():
    state = {"session": {"files": _FailingFiles()}}
    controller = _start_file_transfers(state, _Lifecycle(), [TransferItem("upload", "a.txt", "/a.txt")])
    assert controller.engine.wait(2)
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline and state.get("transfer_sessions"):
        time.sleep(0.01)
    assert state["transfer_sessions"] == set()

@pytest.mark.integration
@pytest.mark.resource
@pytest.mark.concurrency
def test_wx_file_transfer_session_removed_after_cancel():
    files = _BlockingFiles()
    state = {"session": {"files": files}}
    controller = _start_file_transfers(state, _Lifecycle(), [TransferItem("upload", "a.txt", "/a.txt")])
    assert files.started.wait(2)
    controller.cancel()
    files.release.set()
    assert controller.engine.wait(2)
    assert controller.engine.failed[0][1] == "cancelled"
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline and state.get("transfer_sessions"):
        time.sleep(0.01)
    assert state["transfer_sessions"] == set()

@pytest.mark.integration
@pytest.mark.resource
@pytest.mark.concurrency
def test_wx_file_transfer_lifecycle_shutdown_cleans_active_session():
    files = _BlockingFiles()
    lifecycle = _Lifecycle()
    state = {"session": {"files": files}}
    controller = _start_file_transfers(state, lifecycle, [TransferItem("upload", "a.txt", "/a.txt")])
    assert files.started.wait(2)
    for cleanup in lifecycle.cleanups:
        cleanup()
    files.release.set()
    assert controller.engine.wait(2)
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline and state.get("transfer_sessions"):
        time.sleep(0.01)
    assert state["transfer_sessions"] == set()

@pytest.mark.integration
def test_wx_file_context_transfer_reaches_progress_callback():
    files = _Files()
    progress = []
    state = {"session": {"files": files}}
    controller = _start_file_transfers(
        state,
        _Lifecycle(),
        [TransferItem("upload", "a.txt", "/a.txt")],
        on_progress=lambda item, done, total: progress.append((item.src, done, total)),
    )
    assert controller.engine.wait(2)
    assert progress == [("a.txt", 1, 1)]

@pytest.mark.integration
@pytest.mark.semantic
def test_wx_file_transfer_resume_uses_direction_specific_backend_method(tmp_path):
    upload_files = _ResumableFiles("upload")
    upload_state = {"session": {"files": upload_files}, "conflict_policy": "ask"}
    upload = _start_file_transfers(
        upload_state,
        _Lifecycle(),
        [TransferItem("upload", "a.txt", "/work/item")],
        conflict_resolver=lambda _item: "resume",
    )
    assert upload.engine.wait(2)
    assert upload_files.calls == [("resume_upload", "a.txt", "/work/item")]

    # A download conflicts against the LOCAL destination, so it must exist.
    local_destination = tmp_path / "item"
    local_destination.write_bytes(b"partial")
    download_files = _ResumableFiles("download")
    download_state = {"session": {"files": download_files}, "conflict_policy": "ask"}
    download = _start_file_transfers(
        download_state,
        _Lifecycle(),
        [TransferItem("download", "/remote/item", str(local_destination))],
        conflict_resolver=lambda _item: "resume",
    )
    assert download.engine.wait(2)
    assert download_files.calls == [("resume_download", "/remote/item", str(local_destination))]

@pytest.mark.gui
def test_wx_file_transfer_opens_visible_progress_surface():
    wx = pytest.importorskip("wx")
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    parent = wx.Frame(None)
    files = _Files()
    state = {"session": {"files": files}}
    controller = _start_file_transfers(
        state,
        _Lifecycle(),
        [TransferItem("upload", "a.txt", "/a.txt")],
        parent=parent,
    )
    progress_frames = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_transfer_controls")]
    assert progress_frames
    window = progress_frames[-1]
    controls = window._wx_transfer_controls
    deadline = time.monotonic() + 2
    while not controller.engine.wait(0) and time.monotonic() < deadline:
        app.ProcessPendingEvents()
        wx.MilliSleep(5)
    app.ProcessPendingEvents()
    assert controls["gauge"].GetValue() == 1
    assert controls["cancel"].IsEnabled() is False
    window.Close(True)
    parent.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()

@pytest.mark.gui
@pytest.mark.concurrency
@pytest.mark.resource
def test_wx_file_transfer_cancel_button_cancels_controller():
    wx = pytest.importorskip("wx")
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    parent = wx.Frame(None)
    files = _BlockingFiles()
    state = {"session": {"files": files}}
    controller = _start_file_transfers(
        state,
        _Lifecycle(),
        [TransferItem("upload", "a.txt", "/a.txt")],
        parent=parent,
    )
    assert files.started.wait(2)
    window = [item for item in wx.GetTopLevelWindows() if hasattr(item, "_wx_transfer_controls")][-1]
    cancel = window._wx_transfer_controls["cancel"]
    cancel.ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, cancel.GetId()))
    files.release.set()
    assert controller.engine.wait(2)
    app.ProcessPendingEvents()
    assert controller.engine.failed[0][1] == "cancelled"
    assert not cancel.IsEnabled()
    assert state["transfer_sessions"] == set()
    window.Close(True)
    parent.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()
