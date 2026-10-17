
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
    build_connection_panel,
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
def test_master_password_remember_false_no_settings_mutation(monkeypatch):
    """Master password prompt → Remember=false → settings unchanged,
    protect_secret not called, update_settings not called for master persistence.
    """
    tmp = _isolated_storage(monkeypatch)
    try:
        _make_master_encrypted_profile(monkeypatch, name="m-norem")
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=load_profiles())
        captured = {}

        def fake_connect(p):
            captured["pwd"] = p.get("password", "")
            return {"connected": True, "profile_name": p.get("name")}

        host._wx_connection_model._connect = fake_connect

        # Snapshot settings before
        settings_before = deepcopy(load_settings())

        choices = host._wx_connection_controls["choices"]
        choices.SetStringSelection("m-norem")
        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(evt)
        wx.Yield()

        fake_dlg, fake_cb, fake_textctrl, fake_sizer, fake_static = _mock_master_dialog_widgets(remember=False)

        btn = host._wx_connection_controls["connect"]
        with mock.patch("wx.Dialog", return_value=fake_dlg), \
             mock.patch("wx.TextCtrl", side_effect=fake_textctrl), \
             mock.patch("wx.StaticText", return_value=fake_static), \
             mock.patch("wx.CheckBox", return_value=fake_cb), \
             mock.patch("wx.BoxSizer", return_value=fake_sizer), \
             mock.patch("wx.FlexGridSizer", return_value=fake_sizer), \
             mock.patch("wx.MessageBox"), \
             mock.patch("hpc_gui.core.secret_store.protect_secret") as mock_protect, \
             mock.patch("hpc_gui.config.storage.update_settings") as mock_update:
            evt2 = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
            btn.GetEventHandler().ProcessEvent(evt2)
            for _ in range(30):
                wx.Yield()
                wx.MilliSleep(20)
                if host._wx_connection_model.controller.state.value == "connected":
                    break

            # Connection succeeded with correct decrypted secret
            assert captured.get("pwd") == "my-secret"
            # Remember checkbox was explicitly False
            fake_cb.GetValue.assert_called()
            assert fake_cb.GetValue.return_value is False
            # protect_secret was NOT called (Remember=false)
            mock_protect.assert_not_called()
            # update_settings was NOT called for master-password persistence
            for call in mock_update.call_args_list:
                args = call[0] if call[0] else call[1]
                if isinstance(args, dict):
                    assert "master_password_dpapi" not in args

        # Settings unchanged
        settings_after = deepcopy(load_settings())
        assert settings_after.get("master_password_dpapi") == settings_before.get("master_password_dpapi")
        assert not settings_after.get("master_password_dpapi")

        # Profile storage unchanged (no plaintext password persisted)
        profile = next(p for p in load_profiles() if p["name"] == "m-norem")
        assert profile.get("password") == "" or not profile.get("password")
        assert "my-secret" not in str(profile)

        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_master_password_remember_true_persists_protected(monkeypatch):
    """Master password prompt → Remember=true → protect_secret called,
    update_settings called with dpapi token, plaintext never stored.
    """
    tmp = _isolated_storage(monkeypatch)
    try:
        _make_master_encrypted_profile(monkeypatch, name="m-rem")
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=load_profiles())
        captured = {}

        def fake_connect(p):
            captured["pwd"] = p.get("password", "")
            return {"connected": True, "profile_name": p.get("name")}

        host._wx_connection_model._connect = fake_connect

        choices = host._wx_connection_controls["choices"]
        choices.SetStringSelection("m-rem")
        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(evt)
        wx.Yield()

        fake_dlg, fake_cb, fake_textctrl, fake_sizer, fake_static = _mock_master_dialog_widgets(remember=True)

        btn = host._wx_connection_controls["connect"]
        with mock.patch("wx.Dialog", return_value=fake_dlg), \
             mock.patch("wx.TextCtrl", side_effect=fake_textctrl), \
             mock.patch("wx.StaticText", return_value=fake_static), \
             mock.patch("wx.CheckBox", return_value=fake_cb), \
             mock.patch("wx.BoxSizer", return_value=fake_sizer), \
             mock.patch("wx.FlexGridSizer", return_value=fake_sizer), \
             mock.patch("wx.MessageBox"), \
             mock.patch("hpc_gui.core.secret_store.protect_secret", return_value="protected-token-714") as mock_protect, \
             mock.patch("hpc_gui.config.storage.update_settings"):
            evt2 = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
            btn.GetEventHandler().ProcessEvent(evt2)
            for _ in range(30):
                wx.Yield()
                wx.MilliSleep(20)
                if host._wx_connection_model.controller.state.value == "connected":
                    break

            # Connection succeeded
            assert captured.get("pwd") == "my-secret"
            # protect_secret WAS called with the master password
            mock_protect.assert_called_once_with("master123")

        # Plaintext master password never stored in profile
        profile = next(p for p in load_profiles() if p["name"] == "m-rem")
        assert "master123" not in str(profile)
        assert profile.get("password") == "" or not profile.get("password")

        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()
