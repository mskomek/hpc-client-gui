from support.test_wx_file_transfer_integration_shared import (
    PARTIAL,
    REMOTE_FILE,
    SOURCE,
    TransferItem,
    _ConflictFiles,
    _Lifecycle,
    _run_conflict,
    _run_decision,
    _start_file_transfers,
    ftp_backend,
    pytest,
    ssh_backend,
    time,
)

pytestmark = pytest.mark.wx

@pytest.mark.integration
@pytest.mark.semantic
def test_wx_file_transfer_conflict_ask_overwrite():
    assert _run_conflict("ask", lambda _item: "overwrite") == [("upload", "a.txt", "/work/a.txt")]

@pytest.mark.integration
@pytest.mark.semantic
def test_wx_file_transfer_conflict_ask_skip():
    assert _run_conflict("ask", lambda _item: "skip") == []

@pytest.mark.integration
@pytest.mark.semantic
def test_wx_file_transfer_conflict_ask_rename():
    assert _run_conflict("ask", lambda _item: ("rename", "/work/a-1.txt")) == [("upload", "a.txt", "/work/a-1.txt")]

@pytest.mark.integration
@pytest.mark.semantic
def test_wx_file_transfer_conflict_ask_cancel():
    assert _run_conflict("ask", lambda _item: "cancel") == []

@pytest.mark.integration
@pytest.mark.semantic
def test_wx_file_transfer_policy_overwrite():
    assert _run_conflict("overwrite") == [("upload", "a.txt", "/work/a.txt")]

@pytest.mark.integration
@pytest.mark.semantic
def test_wx_file_transfer_policy_skip():
    assert _run_conflict("skip") == []

@pytest.mark.integration
@pytest.mark.semantic
def test_wx_file_transfer_policy_rename():
    assert _run_conflict("rename", lambda _item: ("rename", "/work/a-1.txt")) == [("upload", "a.txt", "/work/a-1.txt")]

@pytest.mark.integration
@pytest.mark.semantic
def test_wx_file_transfer_conflict_ask_uses_gui_decision_seam(monkeypatch):
    wx = pytest.importorskip("wx")
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    parent = wx.Frame(None)
    files = _ConflictFiles()
    state = {"session": {"files": files}, "conflict_policy": "ask"}
    # New conflict UI is a dedicated dialog, not MessageBox; mock the dialog creation to return overwrite
    from hpc_gui import wx_transfer_workspace as _wx_tw
    class _MockDlg:
        def __init__(self, *a, **kw):
            self._wx_conflict_result = {"value": "overwrite"}
        def ShowModal(self):
            return wx.ID_OK
        def Destroy(self):
            pass
    monkeypatch.setattr(_wx_tw, "create_transfer_conflict_dialog", lambda *a, **kw: _MockDlg())
    # also keep old MessageBox mock for fallback
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: wx.YES)
    controller = _start_file_transfers(
        state,
        _Lifecycle(),
        [TransferItem("upload", "a.txt", "/work/a.txt")],
        parent=parent,
    )
    while not controller.engine.wait(0):
        app.ProcessPendingEvents()
        wx.MilliSleep(5)
    app.ProcessPendingEvents()
    assert files.calls == [("upload", "a.txt", "/work/a.txt")]
    parent.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()

@pytest.mark.integration
@pytest.mark.semantic
def test_wx_file_transfer_rename_policy_generates_available_destination():
    wx = pytest.importorskip("wx")
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    parent = wx.Frame(None)
    files = _ConflictFiles()
    state = {"session": {"files": files}, "conflict_policy": "rename"}
    controller = _start_file_transfers(
        state,
        _Lifecycle(),
        [TransferItem("upload", "a.txt", "/work/a.txt")],
        parent=parent,
    )
    assert controller.engine.wait(2)
    assert files.calls == [("upload", "a.txt", "/work/a (1).txt")]
    parent.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()

@pytest.mark.parametrize("choice", ["no", "cancel"])
@pytest.mark.integration
@pytest.mark.semantic
def test_wx_file_transfer_conflict_gui_decline_does_not_upload(monkeypatch, choice):
    wx = pytest.importorskip("wx")
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    parent = wx.Frame(None)
    files = _ConflictFiles()
    state = {"session": {"files": files}, "conflict_policy": "ask"}
    result = wx.NO if choice == "no" else wx.CANCEL
    # Mock dialog to respect old MessageBox-based decline semantics
    from hpc_gui import wx_transfer_workspace as _wx_tw
    decision = "skip" if choice == "no" else "cancel"
    class _MockDlg:
        def __init__(self, *a, **kw):
            self._wx_conflict_result = {"value": decision}
        def ShowModal(self):
            return wx.ID_OK if decision == "skip" else wx.ID_CANCEL
        def Destroy(self):
            pass
    monkeypatch.setattr(_wx_tw, "create_transfer_conflict_dialog", lambda *a, **kw: _MockDlg())
    monkeypatch.setattr(wx, "MessageBox", lambda *_args, **_kwargs: result)
    controller = _start_file_transfers(
        state,
        _Lifecycle(),
        [TransferItem("upload", "a.txt", "/work/a.txt")],
        parent=parent,
    )
    deadline = time.monotonic() + 2
    while not controller.engine.wait(0) and time.monotonic() < deadline:
        app.ProcessPendingEvents()
        wx.MilliSleep(5)
    app.ProcessPendingEvents()
    assert controller.engine.wait(0)
    assert files.calls == []
    parent.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()

@pytest.mark.parametrize("decision,expected", [
    ("overwrite", SOURCE),
    ("resume", PARTIAL + SOURCE[len(PARTIAL):]),
])
@pytest.mark.integration
@pytest.mark.semantic
def test_conflict_decision_drives_ftp_upload_bytes(tmp_path, decision, expected):
    source = tmp_path / "src.bin"
    source.write_bytes(SOURCE)
    files = ftp_backend({REMOTE_FILE: PARTIAL})
    _run_decision(files, TransferItem("upload", str(source), REMOTE_FILE), decision)
    assert bytes(files.ftp.files[REMOTE_FILE]) == expected
    assert files.ftp.transfer_commands == (["STOR"] if decision == "overwrite" else ["APPE"])

@pytest.mark.parametrize("decision,expected", [
    ("overwrite", SOURCE),
    ("resume", PARTIAL + SOURCE[len(PARTIAL):]),
])
@pytest.mark.integration
@pytest.mark.semantic
def test_conflict_decision_drives_ssh_upload_bytes(tmp_path, decision, expected):
    source = tmp_path / "src.bin"
    source.write_bytes(SOURCE)
    files, sftp = ssh_backend({REMOTE_FILE: PARTIAL})
    _run_decision(files, TransferItem("upload", str(source), REMOTE_FILE), decision)
    assert bytes(sftp.store[REMOTE_FILE]) == expected
    assert sftp.modes(REMOTE_FILE) == (["wb"] if decision == "overwrite" else ["ab"])

@pytest.mark.parametrize("decision,expected", [
    ("overwrite", SOURCE),
    ("resume", PARTIAL + SOURCE[len(PARTIAL):]),
])
@pytest.mark.integration
@pytest.mark.semantic
def test_conflict_decision_drives_ssh_download_bytes(tmp_path, decision, expected):
    local = tmp_path / "dst.bin"
    local.write_bytes(PARTIAL)
    files, sftp = ssh_backend({REMOTE_FILE: SOURCE})
    _run_decision(files, TransferItem("download", REMOTE_FILE, str(local)), decision)
    assert local.read_bytes() == expected
    assert sftp.seeks(REMOTE_FILE) == ([] if decision == "overwrite" else [len(PARTIAL)])

@pytest.mark.parametrize("decision,expected", [
    ("overwrite", SOURCE),
    ("resume", PARTIAL + SOURCE[len(PARTIAL):]),
])
@pytest.mark.integration
@pytest.mark.semantic
def test_conflict_decision_drives_ftp_download_bytes(tmp_path, decision, expected):
    local = tmp_path / "dst.bin"
    local.write_bytes(PARTIAL)
    files = ftp_backend({REMOTE_FILE: SOURCE})
    _run_decision(files, TransferItem("download", REMOTE_FILE, str(local)), decision)
    assert local.read_bytes() == expected
    assert files.ftp.rest_offsets == ([None] if decision == "overwrite" else [len(PARTIAL)])
