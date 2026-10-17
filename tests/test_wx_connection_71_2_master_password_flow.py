
pytest_plugins = ('support.test_wx_connection_71_2_shared',)
"""Wave 71.2 — wx Connection final closure tests.

Covers: blank-name Save & Connect, real WxConnectionDialog button event,
master-password wx event chain (success/cancel/wrong), Test Cluster
master-password chain, typed password precedence.

All tests use isolated temp storage and mocked backends; no real HPC cluster.
"""
from support.test_wx_connection_71_2_shared import (
    _isolated_storage,
    _seed_master_dpapi_cache,
    build_connection_panel,
    load_profiles,
    mock,
    pytest,
    storage,
    wx,
)


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_master_password_real_wx_chain(monkeypatch):
    """Real resolver: saved master-encrypted profile -> Connect -> ask_master -> decrypt.

    resolve_password_for_connect and decrypt_with_master are real.
    DPAPI cache is pre-seeded so no wx dialog opens.
    """
    from hpc_gui.core.crypto_master import encrypt_with_master

    tmp = _isolated_storage(monkeypatch)
    try:
        enc = encrypt_with_master("master123", "real-master-secret")
        storage.upsert_profile({
            "name": "m-wx",
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
        host = build_connection_panel(frame, profiles=load_profiles())
        captured = {}

        def fake_connect(p):
            captured["pwd"] = p.get("password", "")
            captured["name"] = p.get("name")
            return {"connected": True, "profile_name": p.get("name")}

        host._wx_connection_model._connect = fake_connect

        choices = host._wx_connection_controls["choices"]
        choices.SetStringSelection("m-wx")
        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(evt)
        wx.Yield()

        btn = host._wx_connection_controls["connect"]
        with mock.patch("wx.MessageBox"):
            evt2 = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
            btn.GetEventHandler().ProcessEvent(evt2)
            for _ in range(30):
                wx.Yield()
                wx.MilliSleep(20)
                if host._wx_connection_model.controller.state.value == "connected":
                    break
            assert captured.get("pwd") == "real-master-secret"
            assert host._wx_connection_model.controller.state.value == "connected"
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_master_password_cancel_blocks_connection(monkeypatch):
    """Connect Selected -> master cancel -> no SSH, no connect, status safe.

    resolve_password_for_connect and decrypt_with_master are real.
    wx.Dialog mocked to return Cancel.
    """
    from hpc_gui.core.crypto_master import encrypt_with_master

    tmp = _isolated_storage(monkeypatch)
    try:
        enc = encrypt_with_master("master123", "secret")
        storage.upsert_profile({
            "name": "m-cancel",
            "host": "h.example",
            "port": 22,
            "username": "user",
            "save_password": True,
            "password_enc": enc.token,
            "password_salt": enc.salt,
        })
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=load_profiles())
        connect_calls = []
        host._wx_connection_model._connect = lambda p: connect_calls.append(p) or {"connected": True}

        choices = host._wx_connection_controls["choices"]
        choices.SetStringSelection("m-cancel")
        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(evt)
        wx.Yield()

        fake_dlg = mock.Mock()
        fake_dlg.ShowModal.return_value = wx.ID_CANCEL
        fake_dlg.Destroy = mock.Mock()
        fake_sizer = mock.Mock()
        fake_static = mock.Mock()
        fake_cb = mock.Mock()
        fake_tc = mock.Mock()

        btn = host._wx_connection_controls["connect"]
        with mock.patch("wx.Dialog", return_value=fake_dlg), \
             mock.patch("wx.TextCtrl", return_value=fake_tc), \
             mock.patch("wx.StaticText", return_value=fake_static), \
             mock.patch("wx.CheckBox", return_value=fake_cb), \
             mock.patch("wx.BoxSizer", return_value=fake_sizer), \
             mock.patch("wx.FlexGridSizer", return_value=fake_sizer), \
             mock.patch("wx.MessageBox"):
            evt2 = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
            btn.GetEventHandler().ProcessEvent(evt2)
            for _ in range(30):
                wx.Yield()
                wx.MilliSleep(20)
            assert len(connect_calls) == 0
            assert host._wx_connection_model.controller.state.value != "connected"
            assert host._wx_connection_controls["add_connection"].IsEnabled()
            assert host._wx_connection_controls["connect"].IsEnabled()
            assert "secret" not in str(load_profiles()[0])
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_wrong_master_password_fails_closed(monkeypatch):
    """Wrong master -> no SSH, no empty password fallback, safe error.

    resolve_password_for_connect and decrypt_with_master are real.
    DPAPI cache returns wrong master, causing real decryption failure.
    """
    from hpc_gui.core.crypto_master import encrypt_with_master

    tmp = _isolated_storage(monkeypatch)
    try:
        enc = encrypt_with_master("master123", "real-secret")
        storage.upsert_profile({
            "name": "m-wrong",
            "host": "h.example",
            "port": 22,
            "username": "user",
            "save_password": True,
            "password_enc": enc.token,
            "password_salt": enc.salt,
        })
        # Seed DPAPI cache with wrong master — this makes _master_ask_factory
        # return "wrong-master" from cache without opening a wx dialog.
        # The real decrypt_with_master("wrong-master", ...) will fail.
        _seed_master_dpapi_cache(monkeypatch, "wrong-master")
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=load_profiles())
        connect_calls = []
        host._wx_connection_model._connect = lambda p: connect_calls.append(p) or {"connected": True}

        choices = host._wx_connection_controls["choices"]
        choices.SetStringSelection("m-wrong")
        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(evt)
        wx.Yield()

        btn = host._wx_connection_controls["connect"]
        with mock.patch("wx.MessageBox") as MockBox:
            evt2 = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
            btn.GetEventHandler().ProcessEvent(evt2)
            for _ in range(50):
                wx.Yield()
                wx.MilliSleep(30)
                if host._wx_connection_model.controller.state.value == "failed":
                    break
            # No SSH connection attempt
            assert len(connect_calls) == 0
            # Status failed
            assert host._wx_connection_model.controller.state.value == "failed"
            # Error shown without secret
            if MockBox.called:
                args, _ = MockBox.call_args
                msg_str = str(args).lower()
                assert "real-secret" not in msg_str
                assert any(w in msg_str for w in ["master", "wrong", "password"])
            # Buttons restored
            assert host._wx_connection_controls["add_connection"].IsEnabled()
            assert host._wx_connection_controls["connect"].IsEnabled()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()
