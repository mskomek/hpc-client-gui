
pytest_plugins = ('support.test_wx_connection_71_4_shared',)
"""Wave 71.4 — wx Connection final micro-closure.

Covers: master-password Remember=false/true settings mutation,
Test Cluster settings mutation, connect_selected return contract,
Save & Connect cancel/wrong-master regression.

All tests use isolated temp storage and mocked backends; no real HPC cluster.
"""
from support.test_wx_connection_71_4_shared import (
    _isolated_storage,
    _make_master_encrypted_profile,
    _mock_master_dialog_widgets,
    deepcopy,
    load_profiles,
    load_settings,
    mock,
    pytest,
    wx,
)


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_cluster_self_test_remember_false_no_settings_mutation(monkeypatch):
    """Test Cluster → master dialog → Remember=false → settings unchanged,
    profiles unchanged, no secret-store write.
    """
    from hpc_gui.wx_connection_dialog import WxConnectionDialog

    tmp = _isolated_storage(monkeypatch)
    try:
        _make_master_encrypted_profile(monkeypatch, name="m-cl-norem")
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        profile = next(p for p in load_profiles() if p["name"] == "m-cl-norem")
        profiles_before = deepcopy(load_profiles())
        settings_before = deepcopy(load_settings())

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

        fake_dlg, fake_cb, fake_textctrl, fake_sizer, fake_static = _mock_master_dialog_widgets(remember=False)

        with mock.patch("hpc_gui.services.cluster_self_test.run_cluster_self_test", side_effect=fake_self_test), \
             mock.patch.object(WxConnectionDialog, "_show_self_test_result", lambda self, r: captured.update({"result": r})), \
             mock.patch.object(WxConnectionDialog, "_show_self_test_error", lambda self, e: captured.update({"error": e})), \
             mock.patch("wx.Dialog", return_value=fake_dlg), \
             mock.patch("wx.TextCtrl", side_effect=fake_textctrl), \
             mock.patch("wx.StaticText", return_value=fake_static), \
             mock.patch("wx.CheckBox", return_value=fake_cb), \
             mock.patch("wx.BoxSizer", return_value=fake_sizer), \
             mock.patch("wx.FlexGridSizer", return_value=fake_sizer), \
             mock.patch("wx.MessageBox"), \
             mock.patch("hpc_gui.core.secret_store.protect_secret") as mock_protect, \
             mock.patch("hpc_gui.config.storage.update_settings") as mock_update:
            btn = dlg.btn_test_cluster
            evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
            btn.GetEventHandler().ProcessEvent(evt)
            for _ in range(30):
                wx.Yield()
                wx.MilliSleep(20)
                if captured.get("pwd"):
                    break
            # Real decrypt produced the credential
            assert captured.get("pwd") == "my-secret"
            # protect_secret NOT called
            mock_protect.assert_not_called()
            # update_settings NOT called for master persistence
            for call in mock_update.call_args_list:
                args = call[0] if call[0] else call[1]
                if isinstance(args, dict):
                    assert "master_password_dpapi" not in args

        # Profiles unchanged
        profiles_after = deepcopy(load_profiles())
        assert profiles_after == profiles_before
        # Settings unchanged
        settings_after = deepcopy(load_settings())
        assert settings_after.get("master_password_dpapi") == settings_before.get("master_password_dpapi")

        dlg.Destroy()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_cluster_self_test_cancel_no_mutation(monkeypatch):
    """Test Cluster → master dialog Cancel → no self-test, no settings change."""
    from hpc_gui.wx_connection_dialog import WxConnectionDialog

    tmp = _isolated_storage(monkeypatch)
    try:
        _make_master_encrypted_profile(monkeypatch, name="m-cl-cancel")
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        profile = next(p for p in load_profiles() if p["name"] == "m-cl-cancel")
        profiles_before = deepcopy(load_profiles())
        settings_before = deepcopy(load_settings())

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
            assert not backend_called[0]
            assert btn.IsEnabled()

        profiles_after = deepcopy(load_profiles())
        settings_after = deepcopy(load_settings())
        assert profiles_after == profiles_before
        assert settings_after.get("master_password_dpapi") == settings_before.get("master_password_dpapi")

        dlg.Destroy()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()
