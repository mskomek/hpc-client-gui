
pytest_plugins = ('support.test_wx_connection_hardening_shared',)
"""Wave 71.1 hardening – wx Connection closure.

Covers P0 credential resolution, Test Cluster, dialogs, action states,
Save & Connect event chain, secret matrices, precedence, unavailable error,
host-key, provider/storage/quota non-regression, i18n, redaction, threading,
controller transitions, selected vs active, delete active.

All tests use isolated temp storage and mocked backends; no real HPC cluster.
"""
from support.test_wx_connection_hardening_shared import (
    ConnectionController,
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
def test_save_and_connect_wx_event_chain(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=[])
        # We will simulate Add -> Save & Connect via real wx events but with fake dialog
        # Patch WxConnectionDialog to simulate user entering profile data and clicking Save & Connect
        from unittest.mock import patch
        # Create a fake dialog that simulates user input and triggers on_save_and_connect
        class FakeDialog:
            def __init__(self, parent, initial_profile=None, mode="add", on_save=None, on_save_and_connect=None):
                self.parent = parent
                self.on_save_and_connect = on_save_and_connect
                self.on_save = on_save
                self._collected = {
                    "name": "new-profile",
                    "host": "h.example",
                    "port": 22,
                    "username": "alice",
                    "project": "",
                    "account": "",
                    "password": "",
                    "key_path": "",
                    "host_key_policy": "accept-new",
                    "x11_forwarding": False,
                    "cli_allowed": False,
                    "keepalive_interval_seconds": 30,
                    "transfer_parallelism": 1,
                    "ssh_timeout": None,
                    "save_password": False,
                    "password_prompt_policy": "when-needed",
                    "system": {},
                    "file_manager": {},
                    "jump_host": {},
                }
            def ShowModal(self):
                # Simulate Save & Connect click – this should trigger exactly one save and one connect
                assert self.on_save_and_connect is not None
                result = self.on_save_and_connect(self._collected)
                assert result is True
                return wx.ID_OK
            def Destroy(self): pass

        # Mock connect backend to capture
        connect_calls = []
        def fake_connect(profile):
            connect_calls.append(profile.get("name"))
            return {"connected": True, "profile_name": profile.get("name")}

        host._wx_connection_model._connect = fake_connect

        with patch("hpc_gui.wx_connection_dialog.WxConnectionDialog", FakeDialog):
            add_btn = host._wx_connection_add_button
            evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, add_btn.GetId())
            add_btn.GetEventHandler().ProcessEvent(evt)
            for _ in range(10):
                wx.Yield()
                wx.MilliSleep(20)
            # Verify save occurred exactly once
            assert len(load_profiles()) == 1
            assert load_profiles()[0]["name"] == "new-profile"
            # Verify profile list refreshed and selected
            choices = host._wx_connection_controls["choices"]
            assert choices.FindString("new-profile") != wx.NOT_FOUND
            assert choices.GetStringSelection() == "new-profile"
            # Verify connect occurred exactly once with saved profile
            # Connect is triggered via Save & Connect's _refresh + connect_selected
            # Our fake_dialog's ShowModal already called on_save_and_connect which does save + connect
            # Need to wait for connect worker
            for _ in range(30):
                wx.Yield()
                wx.MilliSleep(20)
                if host._wx_connection_model.controller.state.value == "connected":
                    break
            assert host._wx_connection_model.controller.state.value == "connected"
            assert connect_calls == ["new-profile"]
            assert host._wx_connection_model.controller.session.get("profile_name") == "new-profile"
            # Visible list contains new entry and selected is new entry
            assert host._wx_connection_controls["status"].GetLabel() != ""
            # No stale pre-save profile object – session profile name matches saved
            assert host._wx_connection_model.controller.session.get("profile_name") == "new-profile"
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
def test_save_failure_prevents_connect(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=[])
        # Patch save to fail
        # Create fake dialog that will attempt save and fail
        class FakeDialogFail:
            def __init__(self, parent, initial_profile=None, mode="add", on_save=None, on_save_and_connect=None):
                self.on_save_and_connect = on_save_and_connect
            def ShowModal(self):
                # Try to save with invalid data – should return False and not connect
                collected = {"name": "", "host": "", "port": 22, "username": "", "system": {}, "file_manager": {}, "jump_host": {}, "save_password": False, "password_prompt_policy": "when-needed"}
                result = self.on_save_and_connect(collected)
                assert result is False, "Save failure must prevent Connect"
                return wx.ID_CANCEL
            def Destroy(self): pass
        connect_calls = []
        host._wx_connection_model._connect = lambda p: connect_calls.append(p) or {"connected": True, "profile_name": p.get("name")}
        with mock.patch("hpc_gui.wx_connection_dialog.WxConnectionDialog", FakeDialogFail):
            add_btn = host._wx_connection_add_button
            evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, add_btn.GetId())
            with mock.patch("wx.MessageBox"):
                add_btn.GetEventHandler().ProcessEvent(evt)
                for _ in range(10):
                    wx.Yield()
                assert len(connect_calls) == 0, "Connect must not run when save fails"
                assert len(load_profiles()) == 0, "No profile should be persisted on save failure"
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.regression
def test_connect_failure_after_save_keeps_profile(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=[])
        class FakeDialog:
            def __init__(self, parent, initial_profile=None, mode="add", on_save=None, on_save_and_connect=None):
                self.on_save_and_connect = on_save_and_connect
                self._collected = {"name": "persisted", "host": "h.example", "port": 22, "username": "user", "system": {}, "file_manager": {}, "jump_host": {}, "save_password": False, "password_prompt_policy": "when-needed"}
            def ShowModal(self):
                result = self.on_save_and_connect(self._collected)
                # Async contract: save succeeded + worker started → True
                assert result is True, f"Save & Connect async start must return True, got {result!r}"
                return wx.ID_OK
            def Destroy(self): pass
        # Make connect fail
        def failing_connect(p):
            raise RuntimeError("synthetic-connect-fail")
        host._wx_connection_model._connect = failing_connect
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
                # Saved profile must remain
                assert len(load_profiles()) == 1
                assert load_profiles()[0]["name"] == "persisted"
                # Visible profile remains
                choices = host._wx_connection_controls["choices"]
                assert choices.FindString("persisted") != wx.NOT_FOUND
                # Async: worker failure → controller failed
                assert host._wx_connection_model.controller.state.value == "failed"
                # No second save
                assert len(load_profiles()) == 1
                # Buttons restored after worker failure
                assert host._wx_connection_controls["add_connection"].IsEnabled()
                assert host._wx_connection_controls["connect"].IsEnabled()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
def test_controller_transitions_and_second_attempt(monkeypatch):
    c = ConnectionController()
    assert c.state.value == "disconnected"
    c.begin_connect()
    assert c.state.value == "connecting"
    c.finish({"profile_name": "p"})
    assert c.state.value == "connected"
    c2 = ConnectionController()
    c2.begin_connect()
    c2.fail()
    assert c2.state.value == "failed"
    # Second attempt must still work
    c2.begin_connect()
    assert c2.state.value == "connecting"
    c2.finish({"profile_name": "p"})
    assert c2.state.value == "connected"

    # Via wx panel
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        storage.upsert_profile({"name": "p", "host": "h.example", "port": 22, "username": "user"})
        host = build_connection_panel(frame, profiles=load_profiles())
        # First fail
        host._wx_connection_model._connect = lambda p: (_ for _ in ()).throw(RuntimeError("fail1"))
        choices = host._wx_connection_controls["choices"]
        choices.SetStringSelection("p")
        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        btn = host._wx_connection_controls["connect"]
        with mock.patch("wx.MessageBox"), mock.patch("wx.MessageDialog"):
            evt2 = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
            btn.GetEventHandler().ProcessEvent(evt2)
            for _ in range(30):
                wx.Yield()
                wx.MilliSleep(20)
                if host._wx_connection_model.controller.state.value == "failed":
                    break
            assert host._wx_connection_model.controller.state.value == "failed"
            # Second succeed
            host._wx_connection_model._connect = lambda p: {"connected": True, "profile_name": p["name"]}
            # Need to re-select (still selected)
            evt3 = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
            btn.GetEventHandler().ProcessEvent(evt3)
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
def test_selected_vs_active_profile(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        storage.upsert_profile({"name": "A", "host": "h1.example", "port": 22, "username": "user"})
        storage.upsert_profile({"name": "B", "host": "h2.example", "port": 22, "username": "user"})
        host = build_connection_panel(frame, profiles=load_profiles())
        host._wx_connection_model._connect = lambda p: {"connected": True, "profile_name": p["name"]}
        choices = host._wx_connection_controls["choices"]
        # Connect A
        choices.SetStringSelection("A")
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
        assert host._wx_connection_model.controller.session.get("profile_name") == "A"
        # Select B without connecting
        choices.SetStringSelection("B")
        evt3 = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(evt3)
        wx.Yield()
        assert host._wx_connection_model.controller.session.get("profile_name") == "A", "Active must remain A after selecting B"
        assert host._wx_connection_model.selected_name == "B", "Selected should be B"
        # UI should not falsely claim B is connected – active_label should show A
        active_label = host._wx_connection_controls["active_label"]
        label = active_label.GetLabel()
        assert "A" in label
        # If B appears, it must be as selected/details, not as active alone
        if "B" in label:
            assert any(word in label for word in ("Selected", "Details", "Seçili", "Detay"))
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
def test_delete_active_profile_blocked(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        storage.upsert_profile({"name": "active", "host": "h.example", "port": 22, "username": "user"})
        host = build_connection_panel(frame, profiles=load_profiles())
        host._wx_connection_model._connect = lambda p: {"connected": True, "profile_name": p["name"]}
        choices = host._wx_connection_controls["choices"]
        choices.SetStringSelection("active")
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
        # Try delete active
        delete_btn = host._wx_connection_controls["delete"]
        with mock.patch("wx.MessageBox") as MockBox:
            evt3 = wx.CommandEvent(wx.EVT_BUTTON.typeId, delete_btn.GetId())
            delete_btn.GetEventHandler().ProcessEvent(evt3)
            for _ in range(5):
                wx.Yield()
            # Should block deletion (check both EN and TR)
            assert len(load_profiles()) == 1, "Active profile must not be deleted while connected"
            assert MockBox.called, "Should show blocked message"
            msg_lower2 = str(MockBox.call_args).lower()
            assert any(word in msg_lower2 for word in ["active", "disconnect", "aktif", "kesin", "bağlantı"])
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()
