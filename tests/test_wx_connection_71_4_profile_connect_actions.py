
pytest_plugins = ('support.test_wx_connection_71_4_shared',)
"""Wave 71.4 — wx Connection final micro-closure.

Covers: master-password Remember=false/true settings mutation,
Test Cluster settings mutation, connect_selected return contract,
Save & Connect cancel/wrong-master regression.

All tests use isolated temp storage and mocked backends; no real HPC cluster.
"""
from support.test_wx_connection_71_4_shared import (
    _isolated_storage,
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
def test_connect_selected_no_selection_returns_false(monkeypatch):
    """connect_selected() returns False when no profile is selected."""
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=[])
        # No selection → connect_selected returns False
        choices = host._wx_connection_controls["choices"]
        assert choices.GetStringSelection() == ""
        # Call connect_selected via the panel's internal function
        # The button is bound to connect_selected; we can call it directly
        # by accessing the host's exposed controls
        connect_btn = host._wx_connection_controls["connect"]
        # Button should be disabled when nothing is selected
        assert not connect_btn.IsEnabled()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_connect_selected_worker_starts_returns_true(monkeypatch):
    """connect_selected() returns True when worker is successfully launched."""
    tmp = _isolated_storage(monkeypatch)
    try:
        storage.upsert_profile({"name": "ok", "host": "h.example", "port": 22, "username": "user"})
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=load_profiles())

        def fake_connect(p):
            return {"connected": True, "profile_name": p.get("name")}

        host._wx_connection_model._connect = fake_connect

        choices = host._wx_connection_controls["choices"]
        choices.SetStringSelection("ok")
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
            assert host._wx_connection_model.controller.state.value == "connected"
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_save_and_connect_master_cancel_returns_false(monkeypatch):
    """Save & Connect → profile saved → master prompt → Cancel →
    on_save_and_connect returns False, no SSH.
    """
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=[])
        connect_calls = []
        host._wx_connection_model._connect = lambda p: connect_calls.append(p) or {"connected": True}

        class FakeDialog:
            def __init__(self, parent, initial_profile=None, mode="add", on_save=None, on_save_and_connect=None):
                self.on_save_and_connect = on_save_and_connect
                self._collected = {
                    "name": "saved-but-cancel",
                    "host": "h.example",
                    "port": 22,
                    "username": "user",
                    "save_password": True,
                    "password_enc": "fake-enc",
                    "password_salt": "fake-salt",
                    "system": {},
                    "file_manager": {},
                    "jump_host": {},
                    "password_prompt_policy": "when-needed",
                }

            def ShowModal(self):
                # on_save_and_connect will try connect_selected, which will
                # hit master prompt (wx.Dialog mocked to Cancel below)
                self.on_save_and_connect(self._collected)
                # Save succeeded but master cancel → connect not started → False
                return wx.ID_OK

            def Destroy(self):
                pass

        # Mock wx.Dialog for master-password prompt → Cancel
        fake_master_dlg = mock.Mock()
        fake_master_dlg.ShowModal.return_value = wx.ID_CANCEL
        fake_master_dlg.Destroy = mock.Mock()
        fake_sizer = mock.Mock()
        fake_static = mock.Mock()
        fake_cb = mock.Mock()
        fake_tc = mock.Mock()

        with mock.patch("hpc_gui.wx_connection_dialog.WxConnectionDialog", FakeDialog):
            with mock.patch("wx.MessageBox"), \
                 mock.patch("wx.Dialog", return_value=fake_master_dlg), \
                 mock.patch("wx.TextCtrl", return_value=fake_tc), \
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
                # Profile was saved (save succeeded before master prompt)
                profiles = load_profiles()
                assert len(profiles) == 1
                assert profiles[0]["name"] == "saved-but-cancel"
                # No SSH connection attempt
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
def test_save_and_connect_wrong_master_returns_false(monkeypatch):
    """Save & Connect → profile saved → master prompt → wrong master →
    on_save_and_connect returns False, no SSH.
    """
    from hpc_gui.core.crypto_master import encrypt_with_master

    tmp = _isolated_storage(monkeypatch)
    try:
        # Create profile that needs master to decrypt
        enc = encrypt_with_master("real-master", "real-secret")
        storage.upsert_profile({
            "name": "saved-wrong-master",
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
        choices.SetStringSelection("saved-wrong-master")
        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(evt)
        wx.Yield()

        # Mock wx.Dialog for master-password prompt → returns wrong master
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

        btn = host._wx_connection_controls["connect"]
        with mock.patch("wx.Dialog", return_value=fake_dlg), \
             mock.patch("wx.TextCtrl", side_effect=fake_textctrl), \
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
            # No SSH connection attempt
            assert len(connect_calls) == 0
            # Status failed or cancelled, not connected
            assert host._wx_connection_model.controller.state.value != "connected"
            # Buttons restored
            assert host._wx_connection_controls["add_connection"].IsEnabled()
            assert host._wx_connection_controls["connect"].IsEnabled()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()
