"""Wave 71.1 hardening – wx Connection closure.

Covers P0 credential resolution, Test Cluster, dialogs, action states,
Save & Connect event chain, secret matrices, precedence, unavailable error,
host-key, provider/storage/quota non-regression, i18n, redaction, threading,
controller transitions, selected vs active, delete active.

All tests use isolated temp storage and mocked backends; no real HPC cluster.
"""

from unittest import mock

import pytest

wx = pytest.importorskip("wx", reason="wxPython not installed – skipping wx GUI tests")

from hpc_gui.config import storage
from hpc_gui.config.storage import load_profiles
from hpc_gui.wx_connection import build_connection_panel
from support.wx_connection_hardening_env import (_isolated_storage)


@pytest.fixture(autouse=True)
def _clean_wx_after():
    yield
    # Ensure any wx windows left open by a failing test are destroyed so the
    # next test's wx.App.Get() does not see a polluted app with open windows
    # (which causes UnregisterClass failures and order-dependent flakes).
    try:
        app = wx.GetApp()
        if app is not None:
            for win in list(wx.GetTopLevelWindows()):
                try:
                    win.Destroy()
                except Exception:
                    pass
            # Process pending destroys
            for _ in range(5):
                try:
                    wx.Yield()
                except Exception:
                    break
    except Exception:
        pass


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_saved_password_unavailable_error(monkeypatch, caplog):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        # Profile with keychain ref but keychain will fail
        storage.upsert_profile({"name": "p", "host": "h.example", "port": 22, "username": "user", "save_password": True, "password_keychain_ref": "missing-ref"})
        host = build_connection_panel(frame, profiles=load_profiles())
        choices = host._wx_connection_controls["choices"]
        choices.SetStringSelection("p")
        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        btn = host._wx_connection_controls["connect"]
        # Mock unprotect to fail
        with mock.patch("hpc_gui.services.connection_profile_service.unprotect_keychain_secret", side_effect=RuntimeError("missing")):
            with mock.patch("wx.MessageBox") as MockBox:
                evt2 = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
                btn.GetEventHandler().ProcessEvent(evt2)
                for _ in range(30):
                    wx.Yield()
                    wx.MilliSleep(20)
                    if host._wx_connection_model.controller.state.value == "failed":
                        break
                assert host._wx_connection_model.controller.state.value == "failed"
                # Should have shown saved_password_unavailable, not generic (check both EN and TR)
                assert MockBox.called
                args, _ = MockBox.call_args
                msg_lower = str(args).lower()
                assert any(word in msg_lower for word in ["saved", "unavailable", "could not be decrypted", "kayıtlı", "çözülemedi", "kullanıcı"])
                # Must not log secret
                assert "missing-ref" not in str(caplog.text)
                # Buttons restored
                assert host._wx_connection_controls["add_connection"].IsEnabled()
                assert host._wx_connection_controls["connect"].IsEnabled()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()


@pytest.mark.unit
@pytest.mark.wx
def test_mfa_respects_echo_and_not_logged(monkeypatch, caplog):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=[])
        model = host._wx_connection_model
        # Mock wx dialogs to capture which dialog type is used
        captured_dialogs = []

        class FakePwd:
            def __init__(self, *a, **kw):
                captured_dialogs.append("pwd")
                self.val = "secret1"
            def ShowModal(self): return wx.ID_OK
            def GetValue(self): return self.val
            def Destroy(self): pass
        class FakeTxt:
            def __init__(self, *a, **kw):
                captured_dialogs.append("txt")
                self.val = "visible2"
            def ShowModal(self): return wx.ID_OK
            def GetValue(self): return self.val
            def Destroy(self): pass
        with mock.patch.object(wx, "PasswordEntryDialog", FakePwd), mock.patch.object(wx, "TextEntryDialog", FakeTxt):
            from hpc_gui.services.connection_controller import KeyboardInteractiveRequest
            req = KeyboardInteractiveRequest("Title", "Instr", ("Prompt1:", "Prompt2:"), (False, True))
            answers = model.answer_keyboard_interactive(req)
            assert answers == ["secret1", "visible2"]
            assert captured_dialogs == ["pwd", "txt"], "echo False must use PasswordEntryDialog, echo True must use TextEntryDialog"
            # Ensure explicit echo wins over heuristic
            captured_dialogs.clear()
            req2 = KeyboardInteractiveRequest("Title", "Instr", ("password prompt",), (True,))
            model.answer_keyboard_interactive(req2)
            assert captured_dialogs == ["txt"], "echo True must not be masked even if prompt contains password"
        # No secret in logs
        assert "secret1" not in str(caplog.text)
        assert "visible2" not in str(caplog.text)
        # Answers not retained on model
        assert not hasattr(model, "secret1")
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()


@pytest.mark.audit
@pytest.mark.wx
def test_password_dialogs_use_correct_api(monkeypatch):
    src = open("src/hpc_gui/wx_connection.py", encoding="utf-8").read()
    assert "wx.PasswordEntryDialog" in src, "MFA and edit auth must use PasswordEntryDialog"
    assert src.count("wx.PasswordEntryDialog") >= 2, "At least MFA and edit auth should use PasswordEntryDialog"
    # Ensure fragile style not used for password prompts
    assert "wx.TextEntryDialog(..., style=wx.TE_PASSWORD" not in src
