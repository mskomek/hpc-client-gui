"""Wave 71.5 — wx Connection micro-hardening.

Covers: begin_connect/Thread.start failure recovery, connect_selected bool
contract proofs, Remember=true settings persistence, Test Cluster
Remember=true, Save & Connect contract fixes.

All tests use isolated temp storage and mocked backends; no real HPC cluster.
"""

from copy import deepcopy
from unittest import mock

import pytest

wx = pytest.importorskip("wx", reason="wxPython not installed")

from hpc_gui.config import storage
from hpc_gui.config.storage import load_profiles
from hpc_gui.core.i18n import current_language, set_language
from hpc_gui.wx_connection import build_connection_panel
from support.wx_connection_715_fixtures import (_isolated_storage, _make_profile)


@pytest.fixture(autouse=True)
def _clean_wx_after():
    original_language = current_language()
    set_language("en")
    yield
    try:
        set_language(original_language)
    finally:
        try:
            app = wx.GetApp()
            if app is not None:
                for win in list(wx.GetTopLevelWindows()):
                    try:
                        win.Destroy()
                    except Exception:
                        pass
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
def test_cluster_remember_true_persists_protected(monkeypatch):
    """Test Cluster → Remember=true → protect_secret + update_settings
    called with protected token, profile unchanged.
    """
    from hpc_gui.wx_connection_dialog import WxConnectionDialog

    tmp = _isolated_storage(monkeypatch)
    try:
        _make_profile("cl-rem", master="master123", secret="cluster-cred")
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        profile = next(p for p in load_profiles() if p["name"] == "cl-rem")
        profiles_before = deepcopy(load_profiles())

        dlg = WxConnectionDialog(frame, initial_profile=profile, mode="edit", on_save=lambda p: True)
        dlg.host_ctrl.SetValue("h.example")
        dlg.username_ctrl.SetValue("user")
        dlg.password_ctrl.SetValue("")

        captured = {}
        def fake_self_test(info, provider=None, project="", account=""):
            captured["pwd"] = info.password
            class R:
                status = "PASS"
                sections = []
            return R()

        fake_pwd_ctrl = mock.Mock()
        fake_pwd_ctrl.GetValue.return_value = "master123"
        fake_pwd_ctrl.SetFocus = mock.Mock()
        fake_confirm_ctrl = mock.Mock()
        fake_confirm_ctrl.GetValue.return_value = ""
        tc_call = [0]
        def fake_textctrl(*args, **kwargs):
            tc_call[0] += 1
            return fake_pwd_ctrl if tc_call[0] == 1 else fake_confirm_ctrl
        fake_cb = mock.Mock()
        fake_cb.GetValue.return_value = True
        fake_dlg = mock.Mock()
        fake_dlg.ShowModal.return_value = wx.ID_OK
        fake_dlg.Destroy = mock.Mock()
        fake_sizer = mock.Mock()
        fake_static = mock.Mock()

        with mock.patch("hpc_gui.services.cluster_self_test.run_cluster_self_test", side_effect=fake_self_test), \
             mock.patch.object(WxConnectionDialog, "_show_self_test_result", lambda self, r: None), \
             mock.patch.object(WxConnectionDialog, "_show_self_test_error", lambda self, e: None), \
             mock.patch("wx.Dialog", return_value=fake_dlg), \
             mock.patch("wx.TextCtrl", side_effect=fake_textctrl), \
             mock.patch("wx.StaticText", return_value=fake_static), \
             mock.patch("wx.CheckBox", return_value=fake_cb), \
             mock.patch("wx.BoxSizer", return_value=fake_sizer), \
             mock.patch("wx.FlexGridSizer", return_value=fake_sizer), \
             mock.patch("wx.MessageBox"), \
             mock.patch("hpc_gui.core.secret_store.protect_secret", return_value="protected-cl-token") as mock_protect, \
             mock.patch("hpc_gui.config.storage.update_settings") as mock_update:
            btn = dlg.btn_test_cluster
            evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
            btn.GetEventHandler().ProcessEvent(evt)
            for _ in range(30):
                wx.Yield()
                wx.MilliSleep(20)
                if captured.get("pwd"):
                    break

            # Self-test received decrypted credential, not master
            assert captured.get("pwd") == "cluster-cred"
            assert captured.get("pwd") != "master123"
            # protect_secret called
            mock_protect.assert_called_once_with("master123")
            # update_settings called with protected token
            dpapi_calls = [c for c in mock_update.call_args_list
                           if c[0] and isinstance(c[0][0], dict) and "master_password_dpapi" in c[0][0]]
            assert len(dpapi_calls) == 1
            assert dpapi_calls[0][0][0]["master_password_dpapi"] == "protected-cl-token"

        # Profile unchanged
        profiles_after = deepcopy(load_profiles())
        assert profiles_after == profiles_before
        # Master not in profile
        profile_after = next(p for p in load_profiles() if p["name"] == "cl-rem")
        assert "master123" not in str(profile_after)
        dlg.Destroy()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_save_and_connect_master_cancel_asserts_result(monkeypatch):
    """Save & Connect → save succeeds → master cancel →
    on_save_and_connect returns False, no SSH.
    """
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=[])
        connect_calls = []
        host._wx_connection_model._connect = lambda p: connect_calls.append(p) or {"connected": True}

        callback_result = [None]
        class FakeDialog:
            def __init__(self, parent, initial_profile=None, mode="add", on_save=None, on_save_and_connect=None):
                self.on_save_and_connect = on_save_and_connect
                self._collected = {
                    "name": "sav-cancel",
                    "host": "h.example", "port": 22, "username": "user",
                    "save_password": True, "password_enc": "fake-enc", "password_salt": "fake-salt",
                    "system": {}, "file_manager": {}, "jump_host": {},
                    "password_prompt_policy": "when-needed",
                }
            def ShowModal(self):
                callback_result[0] = self.on_save_and_connect(self._collected)
                return wx.ID_OK
            def Destroy(self): pass

        fake_master_dlg = mock.Mock()
        fake_master_dlg.ShowModal.return_value = wx.ID_CANCEL
        fake_master_dlg.Destroy = mock.Mock()

        with mock.patch("hpc_gui.wx_connection_dialog.WxConnectionDialog", FakeDialog):
            with mock.patch("wx.MessageBox"), \
                 mock.patch("wx.Dialog", return_value=fake_master_dlg), \
                 mock.patch("wx.TextCtrl"), mock.patch("wx.StaticText"), \
                 mock.patch("wx.CheckBox"), mock.patch("wx.BoxSizer"), \
                 mock.patch("wx.FlexGridSizer"):
                add_btn = host._wx_connection_add_button
                evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, add_btn.GetId())
                add_btn.GetEventHandler().ProcessEvent(evt)
                for _ in range(20):
                    wx.Yield()
                    wx.MilliSleep(20)
                # Callback returned False
                assert callback_result[0] is False, f"Expected False, got {callback_result[0]!r}"
                # Profile was saved
                assert len(load_profiles()) == 1
                assert load_profiles()[0]["name"] == "sav-cancel"
                # No SSH
                assert len(connect_calls) == 0
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_save_and_connect_wrong_master_real_sac(monkeypatch):
    """Real Save & Connect → save succeeds → master prompt → wrong master →
    on_save_and_connect returns False, no SSH.
    """
    from hpc_gui.core.crypto_master import encrypt_with_master

    tmp = _isolated_storage(monkeypatch)
    try:
        # Create master-encrypted profile for save to preserve
        enc = encrypt_with_master("real-master", "real-cred")
        storage.upsert_profile({
            "name": "sac-wrong",
            "host": "h.example", "port": 22, "username": "user",
            "save_password": True, "password_enc": enc.token, "password_salt": enc.salt,
        })
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=load_profiles())
        connect_calls = []
        host._wx_connection_model._connect = lambda p: connect_calls.append(p) or {"connected": True}

        callback_result = [None]

        class FakeDialog:
            def __init__(self, parent, initial_profile=None, mode="add", on_save=None, on_save_and_connect=None):
                self.on_save_and_connect = on_save_and_connect
                self._collected = {
                    "name": "sac-wrong",
                    "host": "h.example", "port": 22, "username": "user",
                    "save_password": True, "password_enc": enc.token, "password_salt": enc.salt,
                    "system": {}, "file_manager": {}, "jump_host": {},
                    "password_prompt_policy": "when-needed",
                }
            def ShowModal(self):
                callback_result[0] = self.on_save_and_connect(self._collected)
                return wx.ID_OK
            def Destroy(self): pass

        # Master dialog returns wrong master
        fake_pwd_ctrl = mock.Mock()
        fake_pwd_ctrl.GetValue.return_value = "wrong-master"
        fake_pwd_ctrl.SetFocus = mock.Mock()
        fake_confirm_ctrl = mock.Mock()
        fake_confirm_ctrl.GetValue.return_value = ""
        tc_call = [0]
        def fake_textctrl(*args, **kwargs):
            tc_call[0] += 1
            return fake_pwd_ctrl if tc_call[0] == 1 else fake_confirm_ctrl
        fake_dlg = mock.Mock()
        fake_dlg.ShowModal.return_value = wx.ID_OK
        fake_dlg.Destroy = mock.Mock()
        fake_sizer = mock.Mock()
        fake_static = mock.Mock()
        fake_cb = mock.Mock()

        with mock.patch("hpc_gui.wx_connection_dialog.WxConnectionDialog", FakeDialog):
            with mock.patch("wx.MessageBox"), \
                 mock.patch("wx.Dialog", return_value=fake_dlg), \
                 mock.patch("wx.TextCtrl", side_effect=fake_textctrl), \
                 mock.patch("wx.StaticText", return_value=fake_static), \
                 mock.patch("wx.CheckBox", return_value=fake_cb), \
                 mock.patch("wx.BoxSizer", return_value=fake_sizer), \
                 mock.patch("wx.FlexGridSizer", return_value=fake_sizer):
                add_btn = host._wx_connection_add_button
                evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, add_btn.GetId())
                add_btn.GetEventHandler().ProcessEvent(evt)
                for _ in range(20):
                    wx.Yield()
                    wx.MilliSleep(20)
                # Callback returned False (wrong master)
                assert callback_result[0] is False, f"Expected False, got {callback_result[0]!r}"
                # No SSH
                assert len(connect_calls) == 0
                # Not connected
                assert host._wx_connection_model.controller.state.value != "connected"
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_save_and_connect_thread_start_failure(monkeypatch):
    """Save & Connect → save succeeds → Thread.start raises →
    on_save_and_connect returns False, profile persists.
    """
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=[])
        connect_calls = []
        host._wx_connection_model._connect = lambda p: connect_calls.append(p) or {"connected": True}

        callback_result = [None]

        class FakeDialog:
            def __init__(self, parent, initial_profile=None, mode="add", on_save=None, on_save_and_connect=None):
                self.on_save_and_connect = on_save_and_connect
                self._collected = {
                    "name": "sac-ts-fail",
                    "host": "h.example", "port": 22, "username": "user",
                    "save_password": False, "system": {}, "file_manager": {},
                    "jump_host": {}, "password_prompt_policy": "when-needed",
                }
            def ShowModal(self):
                callback_result[0] = self.on_save_and_connect(self._collected)
                return wx.ID_OK
            def Destroy(self): pass

        with mock.patch("hpc_gui.wx_connection_dialog.WxConnectionDialog", FakeDialog):
            with mock.patch("wx.MessageBox"), \
                 mock.patch("hpc_gui.wx_connection.Thread") as MockThread:
                mock_thread = mock.Mock()
                mock_thread.start.side_effect = RuntimeError("thread-boom")
                MockThread.return_value = mock_thread
                add_btn = host._wx_connection_add_button
                evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, add_btn.GetId())
                add_btn.GetEventHandler().ProcessEvent(evt)
                for _ in range(10):
                    wx.Yield()
                    wx.MilliSleep(20)
                # Callback returned False
                assert callback_result[0] is False, f"Expected False, got {callback_result[0]!r}"
                # Profile was saved
                assert len(load_profiles()) == 1
                assert load_profiles()[0]["name"] == "sac-ts-fail"
                # No SSH
                assert len(connect_calls) == 0
                # Controller not left connecting
                assert host._wx_connection_model.controller.state.value != "connecting"
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()
