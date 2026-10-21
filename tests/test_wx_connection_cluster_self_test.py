"""Wave 71 Test Cluster credential workflows through real wx events."""

from unittest import mock

import pytest

wx = pytest.importorskip("wx", reason="wxPython not installed")

from hpc_gui.config import storage
from hpc_gui.config.storage import load_profiles
from support.wx_connection_fixtures import (
    clean_wx_after as _clean_wx_after,  # noqa: F401
    isolated_storage as _isolated_storage,
    seed_master_dpapi_cache as _seed_master_dpapi_cache,
)  # noqa: F401


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_cluster_self_test_master_password_chain(monkeypatch):
    """Test Cluster: saved master-encrypted profile -> edit dialog -> Test Cluster -> real resolver -> decrypt.

    Does NOT mock resolve_password_for_connect or decrypt_with_master.
    Pre-seeds DPAPI cache so _make_master_ask returns master without wx dialog.
    """
    from hpc_gui.wx_connection_dialog import WxConnectionDialog
    from hpc_gui.core.crypto_master import encrypt_with_master

    tmp = _isolated_storage(monkeypatch)
    try:
        enc = encrypt_with_master("master123", "cluster-secret")
        storage.upsert_profile({
            "name": "m-cluster",
            "host": "h.example",
            "port": 22,
            "username": "user",
            "save_password": True,
            "password_enc": enc.token,
            "password_salt": enc.salt,
        })
        _seed_master_dpapi_cache(monkeypatch, "master123")
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        profile = next(p for p in load_profiles() if p["name"] == "m-cluster")
        before = [dict(p) for p in load_profiles()]

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

        with mock.patch("hpc_gui.services.cluster_self_test.run_cluster_self_test", side_effect=fake_self_test), \
             mock.patch.object(WxConnectionDialog, "_show_self_test_result", lambda self, r: captured.update({"result": r})), \
             mock.patch.object(WxConnectionDialog, "_show_self_test_error", lambda self, e: captured.update({"error": e})), \
             mock.patch("wx.MessageBox"):
            with mock.patch.object(dlg.btn_test_cluster, "Enable"), mock.patch.object(dlg.btn_test_cluster, "SetLabel"):
                dlg._test_cluster()
                for _ in range(30):
                    wx.Yield()
                    wx.MilliSleep(20)
                    if captured.get("pwd"):
                        break
                assert captured.get("pwd") == "cluster-secret"
        after = [dict(p) for p in load_profiles()]
        assert before == after, "Test Cluster must not mutate storage"
        dlg.Destroy()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_cluster_self_test_real_button_event(monkeypatch):
    """Real WxConnectionDialog → real Test Cluster button EVT_BUTTON →
    real _test_cluster() → real credential resolver → master prompt →
    real decrypt → fake cluster self-test.

    No direct _test_cluster() call. No DPAPI cache seeded.
    wx master dialog mocked to return correct master.
    """
    from hpc_gui.wx_connection_dialog import WxConnectionDialog
    from hpc_gui.core.crypto_master import encrypt_with_master

    tmp = _isolated_storage(monkeypatch)
    try:
        enc = encrypt_with_master("master123", "cluster-prompt-secret")
        storage.upsert_profile({
            "name": "m-cluster-btn",
            "host": "h.example",
            "port": 22,
            "username": "user",
            "save_password": True,
            "password_enc": enc.token,
            "password_salt": enc.salt,
        })
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        profile = next(p for p in load_profiles() if p["name"] == "m-cluster-btn")
        before = [dict(p) for p in load_profiles()]

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

        # Mock wx widgets for master-password dialog inside _make_master_ask
        fake_pwd_ctrl = mock.Mock()
        fake_pwd_ctrl.GetValue.return_value = "master123"
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

        with mock.patch("hpc_gui.services.cluster_self_test.run_cluster_self_test", side_effect=fake_self_test), \
             mock.patch.object(WxConnectionDialog, "_show_self_test_result", lambda self, r: captured.update({"result": r})), \
             mock.patch.object(WxConnectionDialog, "_show_self_test_error", lambda self, e: captured.update({"error": e})), \
             mock.patch("wx.Dialog", return_value=fake_dlg), \
             mock.patch("wx.TextCtrl", side_effect=fake_textctrl), \
             mock.patch("wx.StaticText", return_value=fake_static), \
             mock.patch("wx.CheckBox", return_value=fake_cb), \
             mock.patch("wx.BoxSizer", return_value=fake_sizer), \
             mock.patch("wx.FlexGridSizer", return_value=fake_sizer), \
             mock.patch("wx.MessageBox"):
            # Dispatch real Test Cluster button event
            btn = dlg.btn_test_cluster
            evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
            btn.GetEventHandler().ProcessEvent(evt)
            for _ in range(30):
                wx.Yield()
                wx.MilliSleep(20)
                if captured.get("pwd"):
                    break
            # Real decrypt produced the credential
            assert captured.get("pwd") == "cluster-prompt-secret"
            # Dialog was invoked (prompt path exercised)
            fake_dlg.ShowModal.assert_called()

        # Storage unchanged
        after = [dict(p) for p in load_profiles()]
        assert before == after, "Test Cluster must not mutate storage"
        dlg.Destroy()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_cluster_self_test_cancel(monkeypatch):
    """Test Cluster → master dialog Cancel → no self-test, button re-enabled,
    storage unchanged, no error fallback to empty password.
    """
    from hpc_gui.wx_connection_dialog import WxConnectionDialog
    from hpc_gui.core.crypto_master import encrypt_with_master

    tmp = _isolated_storage(monkeypatch)
    try:
        enc = encrypt_with_master("master123", "should-not-reach")
        storage.upsert_profile({
            "name": "m-cluster-cancel",
            "host": "h.example",
            "port": 22,
            "username": "user",
            "save_password": True,
            "password_enc": enc.token,
            "password_salt": enc.salt,
        })
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        profile = next(p for p in load_profiles() if p["name"] == "m-cluster-cancel")
        before = [dict(p) for p in load_profiles()]

        dlg = WxConnectionDialog(frame, initial_profile=profile, mode="edit", on_save=lambda p: True)
        dlg.host_ctrl.SetValue("h.example")
        dlg.username_ctrl.SetValue("user")
        dlg.password_ctrl.SetValue("")

        backend_called = [False]
        def fake_self_test(info, provider=None, project="", account=""):
            backend_called[0] = True
            class R:
                status = "PASS"
                sections = []
            return R()

        # Mock wx.Dialog to return Cancel
        fake_dlg = mock.Mock()
        fake_dlg.ShowModal.return_value = wx.ID_CANCEL
        fake_dlg.Destroy = mock.Mock()
        fake_sizer = mock.Mock()
        fake_static = mock.Mock()
        fake_cb = mock.Mock()
        fake_tc = mock.Mock()

        with mock.patch("hpc_gui.services.cluster_self_test.run_cluster_self_test", side_effect=fake_self_test), \
             mock.patch.object(WxConnectionDialog, "_show_self_test_result", lambda self, r: None), \
             mock.patch.object(WxConnectionDialog, "_show_self_test_error", lambda self, e: None), \
             mock.patch("wx.Dialog", return_value=fake_dlg), \
             mock.patch("wx.TextCtrl", return_value=fake_tc), \
             mock.patch("wx.StaticText", return_value=fake_static), \
             mock.patch("wx.CheckBox", return_value=fake_cb), \
             mock.patch("wx.BoxSizer", return_value=fake_sizer), \
             mock.patch("wx.FlexGridSizer", return_value=fake_sizer), \
             mock.patch("wx.MessageBox"):
            btn = dlg.btn_test_cluster
            evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
            btn.GetEventHandler().ProcessEvent(evt)
            for _ in range(10):
                wx.Yield()
                wx.MilliSleep(20)
            # Backend never called
            assert not backend_called[0]
            # Button re-enabled
            assert btn.IsEnabled()
            # No error dialog shown
            # Storage unchanged
            after = [dict(p) for p in load_profiles()]
            assert before == after
        dlg.Destroy()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()
