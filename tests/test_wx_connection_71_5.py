
pytest_plugins = ('support.test_wx_connection_71_5_shared',)
"""Wave 71.5 — wx Connection micro-hardening.

Covers: begin_connect/Thread.start failure recovery, connect_selected bool
contract proofs, Remember=true settings persistence, Test Cluster
Remember=true, Save & Connect contract fixes.

All tests use isolated temp storage and mocked backends; no real HPC cluster.
"""
from support.test_wx_connection_71_5_shared import (
    _isolated_storage,
    _make_profile,
    build_connection_panel,
    deepcopy,
    load_profiles,
    mock,
    pytest,
    wx,
)


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_begin_connect_failure_returns_false(monkeypatch):
    """begin_connect() raises → connect_selected returns False,
    controller not connecting, buttons restored, status failed.
    """
    tmp = _isolated_storage(monkeypatch)
    try:
        _make_profile("bc-fail")
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=load_profiles())
        host._wx_connection_model._connect = lambda p: {"connected": True}

        # Select profile
        choices = host._wx_connection_controls["choices"]
        choices.SetStringSelection("bc-fail")
        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(evt)
        wx.Yield()

        # Mock begin_connect to raise
        with mock.patch.object(host._wx_connection_model.controller, "begin_connect", side_effect=RuntimeError("boom")):
            result = host._wx_connection_connect_selected()

        assert result is False
        assert host._wx_connection_model.controller.state.value == "failed"
        assert host._wx_connection_controls["add_connection"].IsEnabled()
        assert host._wx_connection_controls["connect"].IsEnabled()
        assert "failed" in host._wx_connection_controls["status"].GetLabel().lower()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_thread_start_failure_returns_false(monkeypatch):
    """Thread.start() raises → connect_selected returns False,
    controller failed, buttons restored, transient password cleared.
    """
    tmp = _isolated_storage(monkeypatch)
    try:
        _make_profile("ts-fail")
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=load_profiles())
        host._wx_connection_model._connect = lambda p: {"connected": True}

        choices = host._wx_connection_controls["choices"]
        choices.SetStringSelection("ts-fail")
        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(evt)
        wx.Yield()

        # Mock Thread.start to raise
        with mock.patch("hpc_gui.wx_connection.Thread") as MockThread:
            mock_thread = mock.Mock()
            mock_thread.start.side_effect = RuntimeError("thread-start-fail")
            MockThread.return_value = mock_thread
            result = host._wx_connection_connect_selected()

        assert result is False
        assert host._wx_connection_model.controller.state.value == "failed"
        assert host._wx_connection_controls["add_connection"].IsEnabled()
        assert host._wx_connection_controls["connect"].IsEnabled()
        assert "failed" in host._wx_connection_controls["status"].GetLabel().lower()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_connect_selected_no_selection_direct_bool(monkeypatch):
    """connect_selected() → False when no profile selected. Direct assertion."""
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=[])
        connect_calls = []
        host._wx_connection_model._connect = lambda p: connect_calls.append(p) or {"connected": True}

        result = host._wx_connection_connect_selected()
        assert result is False
        assert len(connect_calls) == 0
        assert host._wx_connection_model.controller.state.value != "connecting"
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_connect_selected_worker_starts_direct_bool(monkeypatch):
    """connect_selected() → True when worker successfully launched."""
    tmp = _isolated_storage(monkeypatch)
    try:
        _make_profile("ok-bool")
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=load_profiles())

        def fake_connect(p):
            return {"connected": True, "profile_name": p.get("name")}

        host._wx_connection_model._connect = fake_connect

        choices = host._wx_connection_controls["choices"]
        choices.SetStringSelection("ok-bool")
        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(evt)
        wx.Yield()

        with mock.patch("wx.MessageBox"):
            result = host._wx_connection_connect_selected()
        assert result is True
        # Wait for worker
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
def test_master_remember_true_update_settings_called(monkeypatch):
    """Remember=true → protect_secret called, update_settings called
    with the protected token (not plaintext master).
    """
    tmp = _isolated_storage(monkeypatch)
    try:
        _make_profile("rem-true", master="master123", secret="real-cred")
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=load_profiles())
        captured = {}

        def fake_connect(p):
            captured["pwd"] = p.get("password", "")
            return {"connected": True, "profile_name": p.get("name")}

        host._wx_connection_model._connect = fake_connect

        choices = host._wx_connection_controls["choices"]
        choices.SetStringSelection("rem-true")
        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(evt)
        wx.Yield()

        # Mock wx widgets with Remember=true
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

        btn = host._wx_connection_controls["connect"]
        with mock.patch("wx.Dialog", return_value=fake_dlg), \
             mock.patch("wx.TextCtrl", side_effect=fake_textctrl), \
             mock.patch("wx.StaticText", return_value=fake_static), \
             mock.patch("wx.CheckBox", return_value=fake_cb), \
             mock.patch("wx.BoxSizer", return_value=fake_sizer), \
             mock.patch("wx.FlexGridSizer", return_value=fake_sizer), \
             mock.patch("wx.MessageBox"), \
             mock.patch("hpc_gui.core.secret_store.protect_secret", return_value="protected-token-715") as mock_protect, \
             mock.patch("hpc_gui.config.storage.update_settings") as mock_update:
            evt2 = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
            btn.GetEventHandler().ProcessEvent(evt2)
            for _ in range(30):
                wx.Yield()
                wx.MilliSleep(20)
                if host._wx_connection_model.controller.state.value == "connected":
                    break

            assert captured.get("pwd") == "real-cred"
            # protect_secret called with master password
            mock_protect.assert_called_once_with("master123")
            # update_settings called with protected token (not plaintext)
            dpapi_calls = [c for c in mock_update.call_args_list
                           if c[0] and isinstance(c[0][0], dict) and "master_password_dpapi" in c[0][0]]
            assert len(dpapi_calls) == 1
            assert dpapi_calls[0][0][0]["master_password_dpapi"] == "protected-token-715"

        # Master password never in profile
        profile = next(p for p in load_profiles() if p["name"] == "rem-true")
        assert "master123" not in str(profile)
        assert profile.get("password") == "" or not profile.get("password")
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

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
