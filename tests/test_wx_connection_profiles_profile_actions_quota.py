"""Wave 71 – wx Connection profile management polish tests.

Covers add-button enabled, CRUD, secrets, templates, storage, quota,
advanced SSH, ssh_info mapping, MFA/host-key, action states, i18n.

Uses isolated temp storage and mock/fake backends; never hits a real cluster.
"""
from support.test_wx_connection_profiles_shared import (
    _isolated_storage,
    load_profiles,
    mock,
    pytest,
    quota_gate,
    storage,
    wx,
)


@pytest.mark.integration
def test_quota_states_fail_closed():
    # disabled
    assert quota_gate({"enabled": False, "command_template": "cmd", "backend_id": "x", "consent": True}, backend_ids=["x"], connected=True) == "disabled"
    # not_configured (no command)
    assert quota_gate({"enabled": True, "command_template": "", "backend_id": "x"}, backend_ids=["x"]) == "not_configured"
    # invalid_configuration (bad scope)
    assert quota_gate({"enabled": True, "command_template": "cmd", "backend_id": "x", "scope": "bad"}, backend_ids=["x"], connected=True) == "invalid_configuration"
    # incomplete/unsupported (missing backend)
    assert quota_gate({"enabled": True, "command_template": "cmd", "backend_id": "missing", "consent": True}, backend_ids=["x"], connected=True) == "incomplete/unsupported"
    # provider without quota source -> not_configured via helper
    from hpc_gui.services.quota_monitor import quota_state_for_profile
    assert quota_state_for_profile({"provider_template": {"quota_sources": []}}) == "not_configured"
    assert quota_state_for_profile({"provider_template": {}}) == "not_configured"
    # No guessed command executed – quota_gate never runs command; monitor refresh returns None if not eligible
    from hpc_gui.services.quota_monitor import QuotaMonitor, QuotaBackendRegistry
    monitor = QuotaMonitor(QuotaBackendRegistry([]), lambda c,t,m: "output")
    assert monitor.refresh({"enabled": True, "command_template": "myquota", "backend_id": "unknown"}, connection_id="c", provider_id="p", subject="subj", connected=True) is None
    monitor.close()

@pytest.mark.gui
@pytest.mark.wx
def test_action_enable_disable_states(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        from hpc_gui.wx_connection import build_connection_panel
        frame = wx.Frame(None)
        # No profile selected -> Edit/Duplicate/Delete/Connect disabled
        host = build_connection_panel(frame, profiles=[])
        ctrls = host._wx_connection_controls
        assert not ctrls["edit"].IsEnabled()
        assert not ctrls["duplicate"].IsEnabled()
        assert not ctrls["delete"].IsEnabled()
        assert not ctrls["connect"].IsEnabled()
        assert ctrls["add_connection"].IsEnabled()
        # Add a profile and select
        storage.upsert_profile({"name": "p1", "host": "h.example", "port": 22, "username": "user"})
        host2 = build_connection_panel(frame, profiles=load_profiles())
        ctrls2 = host2._wx_connection_controls
        choices = ctrls2["choices"]
        choices.SetStringSelection("p1")
        # Trigger selection event manually
        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        assert ctrls2["edit"].IsEnabled()
        assert ctrls2["duplicate"].IsEnabled()
        assert ctrls2["delete"].IsEnabled()
        assert ctrls2["connect"].IsEnabled()
        # Do not manually Disable/Enable – production handler must control states
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
def test_action_states_during_connection_and_recovery(monkeypatch):
    """Real production Add/Connect event chain proves button states without manual manipulation."""
    tmp = _isolated_storage(monkeypatch)
    try:
        from hpc_gui.core.i18n import load_language
        load_language("en")
        _wx_app = wx.App.Get() or wx.App(False)
        from hpc_gui.wx_connection import build_connection_panel
        import threading

        storage.upsert_profile({"name": "p1", "host": "h.example", "port": 22, "username": "user"})
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=load_profiles())
        ctrls = host._wx_connection_controls
        choices = ctrls["choices"]
        connect_btn = ctrls["connect"]
        edit_btn = ctrls["edit"]
        duplicate_btn = ctrls["duplicate"]
        delete_btn = ctrls["delete"]
        add_btn = ctrls["add_connection"]
        status = ctrls["status"] if "status" in ctrls else host._wx_connection_controls["status"]
        # Select
        choices.SetStringSelection("p1")
        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(evt)
        for _ in range(3):
            wx.Yield()
        assert edit_btn.IsEnabled() and connect_btn.IsEnabled()
        # Blocking connector
        block = threading.Event()
        called = {"connected": 0}

        def blocking_connect(profile):
            called["connected"] += 1
            block.wait(timeout=5)
            return {"connected": True, "profile_name": profile.get("name", "")}

        host._wx_connection_model._connect = blocking_connect
        # Trigger Connect via real button event
        evt2 = wx.CommandEvent(wx.EVT_BUTTON.typeId, connect_btn.GetId())
        connect_btn.GetEventHandler().ProcessEvent(evt2)
        # Allow worker to start and disable buttons
        for _ in range(10):
            wx.Yield()
            wx.MilliSleep(20)
        # While blocked, production handler must have disabled conflicting actions
        assert not connect_btn.IsEnabled(), "Connect must be disabled while connecting"
        assert not edit_btn.IsEnabled(), "Edit must be disabled while connecting"
        assert not duplicate_btn.IsEnabled(), "Duplicate must be disabled while connecting"
        assert not delete_btn.IsEnabled(), "Delete must be disabled while connecting"
        assert not add_btn.IsEnabled(), "Add must be disabled while connecting per product contract"
        assert "Connecting" in status.GetLabel() or "Bağlan" in status.GetLabel()
        # Release connector – success path
        block.set()
        for _ in range(50):
            wx.Yield()
            wx.MilliSleep(20)
            if "Connected" in status.GetLabel() or "Bağlı" in status.GetLabel():
                break
        assert host._wx_connection_model.controller.state.value == "connected"
        assert "Connected" in status.GetLabel() or "Bağlı" in status.GetLabel()
        assert add_btn.IsEnabled(), "Add restored after success"
        assert edit_btn.IsEnabled(), "Edit restored after success"
        assert called["connected"] == 1
        # Now test failure recovery with a second panel
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
        # Failure case
        storage.save_config({"profiles": [], "settings": {}})
        storage.upsert_profile({"name": "p2", "host": "h.example", "port": 22, "username": "user"})
        frame2 = wx.Frame(None)
        host2 = build_connection_panel(frame2, profiles=load_profiles())
        ctrls2 = host2._wx_connection_controls
        choices2 = ctrls2["choices"]
        connect_btn2 = ctrls2["connect"]
        edit_btn2 = ctrls2["edit"]
        add_btn2 = ctrls2["add_connection"]
        status2 = ctrls2["status"]
        choices2.SetStringSelection("p2")
        evt3 = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices2.GetId())
        choices2.GetEventHandler().ProcessEvent(evt3)
        for _ in range(3):
            wx.Yield()

        def failing_connect(profile):
            raise RuntimeError("synthetic-failure-71")

        host2._wx_connection_model._connect = failing_connect
        # Need to mock MessageBox to avoid modal
        with mock.patch("wx.MessageDialog") as MockDlg, mock.patch("wx.MessageBox") as MockBox:
            MockDlg.return_value.ShowModal.return_value = wx.ID_OK
            MockDlg.return_value.Destroy = mock.Mock()
            evt4 = wx.CommandEvent(wx.EVT_BUTTON.typeId, connect_btn2.GetId())
            connect_btn2.GetEventHandler().ProcessEvent(evt4)
            for _ in range(50):
                wx.Yield()
                wx.MilliSleep(20)
                if "failed" in status2.GetLabel().lower() or "başarısız" in status2.GetLabel().lower():
                    break
            assert host2._wx_connection_model.controller.state.value == "failed"
            assert "failed" in status2.GetLabel().lower() or "başarısız" in status2.GetLabel().lower()
            # No control stays stuck disabled – production callback must restore
            assert add_btn2.IsEnabled(), "Add must be restored after failure"
            assert edit_btn2.IsEnabled(), "Edit must be restored after failure"
            assert connect_btn2.IsEnabled(), "Connect must be restored after failure"
            # Error string must not contain secret
            if MockBox.called:
                args, _ = MockBox.call_args
                assert "s3cret" not in str(args)
                assert "synthetic-failure-71" in str(args) or "Connection" in str(args)
        frame2.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
def test_dialog_save_and_connect_calls_one_callback(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        from hpc_gui.wx_connection_dialog import WxConnectionDialog

        frame = wx.Frame(None)
        calls = []
        dlg = WxConnectionDialog(
            frame,
            on_save=lambda _profile: calls.append("save") or True,
            on_save_and_connect=lambda _profile: calls.append("save_and_connect") or True,
        )
        dlg._collect_profile = lambda: {"name": "p", "host": "h.example"}
        with mock.patch.object(dlg.dlg, "EndModal") as end_modal:
            dlg._save_and_connect_clicked()
        assert calls == ["save_and_connect"]
        end_modal.assert_called_once_with(wx.ID_OK)
        dlg.Destroy()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.contract
def test_quota_profile_lookup_supports_nested_provider_template():
    from hpc_gui.services.quota_monitor import quota_state_for_profile

    profile = {"system": {"provider_template": {"quota_sources": [{"enabled": False, "command_template": "quota"}]}}}
    assert quota_state_for_profile(profile) == "disabled"

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_real_dialog_rename_onto_existing_name_rejected(monkeypatch):
    """Real WxConnectionDialog (edit beta -> rename alpha) -> real Save button -> rejected."""
    from hpc_gui.core.i18n import t, load_language
    from hpc_gui.services.connection_profile_service import save_profile as svc_save
    from hpc_gui.wx_connection_dialog import WxConnectionDialog

    load_language("en")
    expected = 'Profile name "alpha" is already used by another profile. Choose a different name.'
    assert t("connection.rename_name_taken").format(name="alpha") == expected
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        storage.upsert_profile({"name": "alpha", "host": "h1.example", "port": 22, "username": "u1"})
        storage.upsert_profile({"name": "beta", "host": "h2.example", "port": 22, "username": "u2"})
        beta = next(p for p in load_profiles() if p.get("name") == "beta")

        frame = wx.Frame(None)
        shown = []

        def panel_like_on_save(collected):
            # Mirrors build_connection_panel._handle_save for the edit path.
            plain = str(collected.get("password", "") or "")
            save_pw = bool(collected.get("save_password", False))
            prompt_policy = str(collected.get("password_prompt_policy") or "when-needed")
            initial = next((p for p in load_profiles() if p.get("name") == "beta"), None)
            try:
                svc_save(
                    collected,
                    initial_profile=initial,
                    plain_password=plain,
                    save_password=save_pw,
                    prompt_policy=prompt_policy,
                    ask_master=None,
                    original_name_override="beta",
                )
            except ValueError as exc:
                msg = str(exc)
                if msg.startswith("profile_name_taken:"):
                    taken = msg.split(":", 1)[1].strip()
                    msg = t("connection.rename_name_taken").format(name=taken)
                shown.append(msg)
                return False
            return True

        dlg = WxConnectionDialog(
            frame,
            initial_profile=beta,
            mode="edit",
            on_save=panel_like_on_save,
        )
        assert dlg.profile_name_ctrl.GetValue() == "beta"
        dlg.profile_name_ctrl.SetValue("alpha")

        with mock.patch.object(dlg.dlg, "EndModal") as end_modal:
            btn = dlg.btn_save
            evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
            btn.GetEventHandler().ProcessEvent(evt)
            for _ in range(10):
                wx.Yield()

        end_modal.assert_not_called()
        assert shown == [expected]
        rows = load_profiles()
        assert len([p for p in rows if p.get("name") == "alpha"]) == 1
        assert len([p for p in rows if p.get("name") == "beta"]) == 1
        assert next(p for p in rows if p.get("name") == "beta")["host"] == "h2.example"
        dlg.Destroy()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_panel_save_maps_rename_conflict_to_warning(monkeypatch):
    """Real build_connection_panel._handle_save rejects a rename-onto-existing save."""
    from hpc_gui.core.i18n import t, load_language
    from hpc_gui.wx_connection import build_connection_panel

    load_language("en")
    expected = 'Profile name "alpha" is already used by another profile. Choose a different name.'
    assert t("connection.rename_name_taken").format(name="alpha") == expected
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        storage.upsert_profile({"name": "alpha", "host": "h1.example", "port": 22, "username": "u1"})
        storage.upsert_profile({"name": "beta", "host": "h2.example", "port": 22, "username": "u2"})

        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=load_profiles())

        conflicting = {
            "name": "alpha",
            "host": "h2x.example",
            "port": 22,
            "username": "u2",
            "password": "",
            "save_password": False,
            "password_prompt_policy": "when-needed",
        }

        class FakeDialog:
            def __init__(self, parent, initial_profile=None, mode="add", on_save=None, on_save_and_connect=None):
                assert mode == "edit"
                self._result = on_save(conflicting) if on_save else False

            def ShowModal(self):
                return wx.ID_CANCEL

            def Destroy(self):
                pass

        shown = []
        with mock.patch("hpc_gui.wx_connection_dialog.WxConnectionDialog", FakeDialog):
            with mock.patch.object(wx, "MessageBox", side_effect=lambda msg, *a, **k: shown.append(msg) or wx.ID_OK):
                host._wx_connection_open_dialog("edit", "beta")
                for _ in range(5):
                    wx.Yield()

        assert shown == [expected]
        rows = load_profiles()
        assert sorted(p["name"] for p in rows) == ["alpha", "beta"]
        assert next(p for p in rows if p.get("name") == "beta")["host"] == "h2.example"
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()
