
pytest_plugins = ('support.test_wx_connection_71_2_shared',)
"""Wave 71.2 — wx Connection final closure tests.

Covers: blank-name Save & Connect, real WxConnectionDialog button event,
master-password wx event chain (success/cancel/wrong), Test Cluster
master-password chain, typed password precedence.

All tests use isolated temp storage and mocked backends; no real HPC cluster.
"""
from support.test_wx_connection_71_2_shared import (
    _isolated_storage,
    build_connection_panel,
    load_profiles,
    mock,
    pytest,
    wx,
)


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_blank_name_save_and_connect_uses_canonical_name(monkeypatch):
    """Blank profile name must produce alice@login.cluster.edu, not login.cluster.edu."""
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=[])
        connect_calls = []

        def fake_connect(profile):
            connect_calls.append(dict(profile))
            return {"connected": True, "profile_name": profile.get("name", "")}

        host._wx_connection_model._connect = fake_connect

        class FakeDialog:
            def __init__(self, parent, initial_profile=None, mode="add", on_save=None, on_save_and_connect=None):
                self.on_save_and_connect = on_save_and_connect
                self._collected = {
                    "name": "",
                    "host": "login.cluster.edu",
                    "port": 22,
                    "username": "alice",
                    "system": {},
                    "file_manager": {},
                    "jump_host": {},
                    "save_password": False,
                    "password_prompt_policy": "when-needed",
                }
            def ShowModal(self):
                result = self.on_save_and_connect(self._collected)
                assert result is True, "Save & Connect with blank name must succeed"
                return wx.ID_OK
            def Destroy(self): pass

        with mock.patch("hpc_gui.wx_connection_dialog.WxConnectionDialog", FakeDialog):
            with mock.patch("wx.MessageBox"):
                add_btn = host._wx_connection_add_button
                evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, add_btn.GetId())
                add_btn.GetEventHandler().ProcessEvent(evt)
                for _ in range(30):
                    wx.Yield()
                    wx.MilliSleep(20)
                    if host._wx_connection_model.controller.state.value == "connected":
                        break
            # Exactly one profile saved with canonical name
            profiles = load_profiles()
            assert len(profiles) == 1
            assert profiles[0]["name"] == "alice@login.cluster.edu"
            # No duplicate login.cluster.edu profile
            assert not any(p.get("name") == "login.cluster.edu" for p in profiles)
            # Selection is the canonical name
            choices = host._wx_connection_controls["choices"]
            assert choices.GetStringSelection() == "alice@login.cluster.edu"
            # Connected with canonical name
            assert host._wx_connection_model.controller.state.value == "connected"
            assert len(connect_calls) == 1
            assert connect_calls[0]["name"] == "alice@login.cluster.edu"
            assert host._wx_connection_model.controller.session.get("profile_name") == "alice@login.cluster.edu"
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_real_wx_dialog_save_and_connect_button_event(monkeypatch):
    """Real WxConnectionDialog -> real Save & Connect wx.Button -> wx.EVT_BUTTON."""
    from hpc_gui.wx_connection_dialog import WxConnectionDialog

    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=[])

        saved = []

        def panel_on_save(collected):
            from hpc_gui.services.connection_profile_service import save_profile as svc_save
            with mock.patch("hpc_gui.services.connection_profile_service.keychain_available", return_value=False), \
                 mock.patch("hpc_gui.services.connection_profile_service.os_secret_store_available", return_value=False):
                result = svc_save(
                    collected,
                    initial_profile=None,
                    plain_password="",
                    save_password=False,
                    prompt_policy="when-needed",
                )
            saved.append(result)
            return True

        def panel_on_save_and_connect(collected):
            result = panel_on_save(collected)
            if not result:
                return False
            saved_name = str(saved[-1].get("name", ""))
            host._wx_connection_refresh(select_name=saved_name)
            choices = host._wx_connection_controls["choices"]
            idx = choices.FindString(saved_name)
            if idx != wx.NOT_FOUND:
                choices.SetSelection(idx)
            return True

        dlg = WxConnectionDialog(
            frame,
            initial_profile=None,
            mode="add",
            on_save=panel_on_save,
            on_save_and_connect=panel_on_save_and_connect,
        )
        dlg.profile_name_ctrl.SetValue("real-event-test")
        dlg.host_ctrl.SetValue("h.example")
        dlg.username_ctrl.SetValue("user")

        # Dispatch real Save & Connect button event
        btn = dlg.btn_save_connect
        evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
        btn.GetEventHandler().ProcessEvent(evt)
        for _ in range(10):
            wx.Yield()

        # Profile saved exactly once
        assert len(saved) == 1
        assert saved[0]["name"] == "real-event-test"
        assert len(load_profiles()) == 1
        # List shows the profile
        choices = host._wx_connection_controls["choices"]
        assert choices.FindString("real-event-test") != wx.NOT_FOUND
        dlg.Destroy()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()
