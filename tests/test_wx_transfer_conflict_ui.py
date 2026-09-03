# ruff: noqa
import pytest
wx = pytest.importorskip("wx")
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.services.transfer_session_controller import TransferSessionController
from hpc_gui.wx_transfer_workspace import create_transfer_conflict_dialog
from hpc_gui.core.i18n import load_language

@pytest.fixture
def wx_app():
    load_language("en")
    app=wx.App(False)
    yield app
    for w in wx.GetTopLevelWindows():
        if w: w.Destroy()
    app.ProcessPendingEvents()
    app.Destroy()

class _Files:
    def __init__(self, existing=None):
        self.existing=set(existing or [])
        self.calls=[]
    def exists(self, path): return path in self.existing
    def upload(self, src, dst):
        self.calls.append(("upload", src, dst))
        self.existing.add(dst)
    def download(self, src, dst):
        self.calls.append(("download", src, dst))

class _ResumeFiles(_Files):
    # simulate SSH backend with resume support marker
    supports_resume=True
    def upload(self, src, dst):
        # if dst exists and we are resuming, we should have partial handling
        self.calls.append(("upload_resume", src, dst))

def test_wx_conflict_dialog_has_required_buttons(wx_app):
    parent=wx.Frame(None)
    files=_Files(existing={"/dst/file.txt"})
    item=TransferItem("upload","src.txt","/dst/file.txt")
    dlg=create_transfer_conflict_dialog(parent, files, item)
    assert dlg is not None
    ctrls=dlg._wx_conflict_controls
    assert ctrls["overwrite"] is not None
    assert ctrls["skip"] is not None
    assert ctrls["rename"] is not None
    assert ctrls["cancel"] is not None
    dlg.Destroy()
    parent.Destroy()
    wx_app.ProcessPendingEvents()

def test_wx_conflict_dialog_hides_resume_when_backend_cannot_resume(wx_app):
    parent=wx.Frame(None)
    files=_Files(existing={"/dst/file.txt"})  # generic, no resume
    item=TransferItem("upload","src","/dst/file.txt")
    dlg=create_transfer_conflict_dialog(parent, files, item)
    assert dlg._wx_conflict_controls["resume"] is None
    assert dlg._wx_conflict_resume_supported is False
    dlg.Destroy()
    parent.Destroy()
    wx_app.ProcessPendingEvents()

def test_wx_conflict_dialog_shows_resume_when_backend_supports(wx_app):
    parent=wx.Frame(None)
    # use name that triggers _supports_resume via class name
    # we cannot instantiate without ssh, so use mock with supports_resume True
    files=_ResumeFiles(existing={"/dst/file.txt"})
    item=TransferItem("upload","src","/dst/file.txt")
    dlg=create_transfer_conflict_dialog(parent, files, item)
    assert dlg._wx_conflict_controls["resume"] is not None
    assert dlg._wx_conflict_resume_supported is True
    dlg.Destroy()
    parent.Destroy()
    wx_app.ProcessPendingEvents()

def test_wx_conflict_rename_flow_validates_and_returns_rename(wx_app, monkeypatch):
    parent=wx.Frame(None)
    files=_Files(existing={"/dst/existing.txt"})
    item=TransferItem("upload","src.txt","/dst/file.txt")
    dlg=create_transfer_conflict_dialog(parent, files, item)
    # mock TextEntryDialog to return new valid name
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: _Dialog("renamed.txt"))
    # simulate rename button click
    rename_btn=dlg._wx_conflict_controls["rename"]
    # need to trigger its handler; we can directly call the bound handler via ProcessEvent
    # Instead directly simulate user clicking rename: call the handler logic via button event
    # The handler will open TextEntryDialog and set result to ("rename", "/dst/renamed.txt")
    event=wx.CommandEvent(wx.wxEVT_BUTTON, rename_btn.GetId())
    rename_btn.ProcessEvent(event)
    # after rename handler, dialog should have ended modal with OK and result set
    # our rename handler calls dlg.EndModal, but since not shown modally, we need to check result dict directly
    # In our implementation, result is set before EndModal
    assert dlg._wx_conflict_result["value"][0]=="rename"
    assert dlg._wx_conflict_result["value"][1]=="/dst/renamed.txt"
    dlg.Destroy()
    parent.Destroy()
    wx_app.ProcessPendingEvents()

def test_wx_conflict_rename_rejects_empty_and_shows_error(wx_app, monkeypatch):
    parent=wx.Frame(None)
    files=_Files(existing={"/dst/file.txt"})
    item=TransferItem("upload","src","/dst/file.txt")
    dlg=create_transfer_conflict_dialog(parent, files, item)
    # first attempt empty, second valid
    dialogs=[_Dialog(""), _Dialog("valid.txt")]
    def fake(*a, **k):
        return dialogs.pop(0)
    errors=[]
    monkeypatch.setattr(wx, "TextEntryDialog", fake)
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: errors.append(a) or wx.OK)
    rename_btn=dlg._wx_conflict_controls["rename"]
    event=wx.CommandEvent(wx.wxEVT_BUTTON, rename_btn.GetId())
    rename_btn.ProcessEvent(event)
    # after empty rejection, should have retried and then succeeded with valid.txt
    assert errors
    assert dlg._wx_conflict_result["value"][1]=="/dst/valid.txt"
    dlg.Destroy()
    parent.Destroy()
    wx_app.ProcessPendingEvents()

def test_wx_conflict_rename_rejects_path_separator(wx_app, monkeypatch):
    parent=wx.Frame(None)
    files=_Files(existing={"/dst/file.txt"})
    item=TransferItem("upload","src","/dst/file.txt")
    dlg=create_transfer_conflict_dialog(parent, files, item)
    dialogs=[_Dialog("bad/name"), _Dialog("good.txt")]
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: dialogs.pop(0))
    errors=[]
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: errors.append(a) or wx.OK)
    dlg._wx_conflict_controls["rename"].ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, dlg._wx_conflict_controls["rename"].GetId()))
    assert errors
    assert dlg._wx_conflict_result["value"][1]=="/dst/good.txt"
    dlg.Destroy()
    parent.Destroy()
    wx_app.ProcessPendingEvents()

def test_wx_conflict_rename_rejects_existing_destination(wx_app, monkeypatch):
    parent=wx.Frame(None)
    files=_Files(existing={"/dst/file.txt", "/dst/taken.txt"})
    item=TransferItem("upload","src","/dst/file.txt")
    dlg=create_transfer_conflict_dialog(parent, files, item)
    dialogs=[_Dialog("taken.txt"), _Dialog("free.txt")]
    monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: dialogs.pop(0))
    errors=[]
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: errors.append(a) or wx.OK)
    dlg._wx_conflict_controls["rename"].ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, dlg._wx_conflict_controls["rename"].GetId()))
    assert errors
    assert dlg._wx_conflict_result["value"][1]=="/dst/free.txt"
    dlg.Destroy()
    parent.Destroy()
    wx_app.ProcessPendingEvents()

def test_wx_conflict_dialog_hides_resume_without_explicit_backend_capability(wx_app):
    parent=wx.Frame(None)
    # Backend with class name SSHFilesBackend but no explicit supports_resume must NOT trigger resume
    FakeSSH = type("SSHFilesBackend", (), {"exists": lambda self, p: True})()
    item=TransferItem("upload","src","/dst/file.txt")
    dlg=create_transfer_conflict_dialog(parent, FakeSSH, item)
    assert dlg._wx_conflict_controls["resume"] is None
    assert dlg._wx_conflict_resume_supported is False
    dlg.Destroy()
    # Also generic fake with source containing REST/APPE must not trigger
    class FakeFTP:
        def exists(self, p): return True
        # simulate source containing REST/APPE if inspected, but should still be hidden
        def upload(self, s, d): pass
    FakeFTP.__name__ = "FTPFilesBackend"
    # we don't set supports_resume, so should be hidden
    fake_ftp = FakeFTP()
    dlg2=create_transfer_conflict_dialog(parent, fake_ftp, item)
    assert dlg2._wx_conflict_controls["resume"] is None
    dlg2.Destroy()
    parent.Destroy()
    wx_app.ProcessPendingEvents()

def test_wx_conflict_dialog_overwrite_skip_cancel_return_values(wx_app):
    parent=wx.Frame(None)
    files=_Files()
    item=TransferItem("upload","src","/dst/file.txt")
    dlg=create_transfer_conflict_dialog(parent, files, item)
    # overwrite
    dlg._wx_conflict_controls["overwrite"].ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, dlg._wx_conflict_controls["overwrite"].GetId()))
    assert dlg._wx_conflict_result["value"]=="overwrite"
    dlg.Destroy()
    dlg2=create_transfer_conflict_dialog(parent, files, item)
    dlg2._wx_conflict_controls["skip"].ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, dlg2._wx_conflict_controls["skip"].GetId()))
    assert dlg2._wx_conflict_result["value"]=="skip"
    dlg2.Destroy()
    dlg3=create_transfer_conflict_dialog(parent, files, item)
    dlg3._wx_conflict_controls["cancel"].ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, dlg3._wx_conflict_controls["cancel"].GetId()))
    assert dlg3._wx_conflict_result["value"]=="cancel"
    dlg3.Destroy()
    parent.Destroy()
    wx_app.ProcessPendingEvents()

class _Dialog:
    def __init__(self, value): self.value=value
    def ShowModal(self): return wx.ID_OK
    def GetValue(self): return self.value
    def Destroy(self): pass
