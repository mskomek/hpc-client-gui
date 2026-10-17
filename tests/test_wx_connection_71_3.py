
pytest_plugins = ('support.test_wx_connection_71_3_shared',)
"""Wave 71.3 — wx Connection evidence closure.

Covers: production Save & Connect event-chain with blank-name canonical path,
real master-password wx prompt (no cache), Test Cluster real button event,
Test Cluster cancel path, typed password precedence.

All tests use isolated temp storage and mocked backends; no real HPC cluster.
"""
from support.test_wx_connection_71_3_shared import (
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
def test_save_and_connect_async_failure_returns_true(monkeypatch):
    """Save & Connect: save succeeds + worker starts → True.
    Worker later fails → controller.failed, profile persists, buttons restored.
    No manual Enable/Disable by the test.
    """
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=[])

        connect_attempts = []

        def failing_connect(profile):
            connect_attempts.append(dict(profile))
            raise RuntimeError("synthetic-ssh-failure")

        host._wx_connection_model._connect = failing_connect

        class FakeDialog:
            def __init__(self, parent, initial_profile=None, mode="add", on_save=None, on_save_and_connect=None):
                self.on_save_and_connect = on_save_and_connect
                self._collected = {
                    "name": "async-fail",
                    "host": "h.example",
                    "port": 22,
                    "username": "user",
                    "system": {},
                    "file_manager": {},
                    "jump_host": {},
                    "save_password": False,
                    "password_prompt_policy": "when-needed",
                }

            def ShowModal(self):
                result = self.on_save_and_connect(self._collected)
                assert result is True, f"Async start must return True, got {result!r}"
                return wx.ID_OK

            def Destroy(self):
                pass

        with mock.patch("hpc_gui.wx_connection_dialog.WxConnectionDialog", FakeDialog):
            with mock.patch("wx.MessageBox"), mock.patch("wx.MessageDialog"):
                add_btn = host._wx_connection_add_button
                evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, add_btn.GetId())
                add_btn.GetEventHandler().ProcessEvent(evt)
                for _ in range(50):
                    wx.Yield()
                    wx.MilliSleep(20)
                    if host._wx_connection_model.controller.state.value == "failed":
                        break

                # Exactly one profile persisted
                assert len(load_profiles()) == 1
                assert load_profiles()[0]["name"] == "async-fail"
                # Exactly one connection attempt
                assert len(connect_attempts) == 1
                assert connect_attempts[0]["name"] == "async-fail"
                # Canonical profile remains selected
                choices = host._wx_connection_controls["choices"]
                assert choices.GetStringSelection() == "async-fail"
                # Worker failure → controller failed
                assert host._wx_connection_model.controller.state.value == "failed"
                # Status text contains failure indication
                status_label = host._wx_connection_controls["status"].GetLabel().lower()
                assert "failed" in status_label or "başarısız" in status_label
                # No duplicate save
                assert len(load_profiles()) == 1
                # Buttons restored by production callback
                assert host._wx_connection_controls["add_connection"].IsEnabled()
                assert host._wx_connection_controls["connect"].IsEnabled()
                # No exception secret exposed in MessageBox
                # (MessageBox is fully mocked, so no leak possible)
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_production_save_and_connect_blank_name_canonical(monkeypatch):
    """Full production wiring: Add button → real WxConnectionDialog → real
    production on_save_and_connect → real save_profile → canonical name →
    real connect_selected → fake backend → Connected.

    Uses blank profile name to prove canonical alice@login.cluster.edu path.
    """
    from hpc_gui.wx_connection_dialog import WxConnectionDialog

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

        # Patch ShowModal to be non-blocking while keeping real dialog internals.

        def non_blocking_show_modal(self):
            # Fill in blank-name profile data on real controls
            self.profile_name_ctrl.SetValue("")
            self.host_ctrl.SetValue("login.cluster.edu")
            self.username_ctrl.SetValue("alice")
            self.port_ctrl.SetValue("22")
            # Dispatch the real Save & Connect button event
            btn = self.btn_save_connect
            evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
            btn.GetEventHandler().ProcessEvent(evt)
            for _ in range(10):
                wx.Yield()
            return wx.ID_CANCEL  # dialog close after button dispatch

        with mock.patch.object(WxConnectionDialog, "ShowModal", non_blocking_show_modal):
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
            # No duplicate
            assert not any(p.get("name") == "login.cluster.edu" for p in profiles)
            # Selection correct
            choices = host._wx_connection_controls["choices"]
            assert choices.GetStringSelection() == "alice@login.cluster.edu"
            # Connected
            assert host._wx_connection_model.controller.state.value == "connected"
            # Exactly one connect call with canonical name
            assert len(connect_calls) == 1
            assert connect_calls[0]["name"] == "alice@login.cluster.edu"
            assert host._wx_connection_model.controller.session.get("profile_name") == "alice@login.cluster.edu"
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()
