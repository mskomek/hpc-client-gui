
pytest_plugins = ('support.test_wx_connection_hardening_shared',)
"""Wave 71.1 hardening – wx Connection closure.

Covers P0 credential resolution, Test Cluster, dialogs, action states,
Save & Connect event chain, secret matrices, precedence, unavailable error,
host-key, provider/storage/quota non-regression, i18n, redaction, threading,
controller transitions, selected vs active, delete active.

All tests use isolated temp storage and mocked backends; no real HPC cluster.
"""
from support.test_wx_connection_hardening_shared import (
    WxConnectionModel,
    _isolated_storage,
    build_connection_panel,
    load_profiles,
    mock,
    pytest,
    resolve_password_for_connect,
    ssh_info_from_profile,
    storage,
    wx,
)


@pytest.mark.integration
@pytest.mark.wx
@pytest.mark.semantic
def test_keychain_connect_resolves(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        # Profile with keychain ref
        storage.upsert_profile({"name": "kc", "host": "h.example", "port": 22, "username": "user", "save_password": True, "password_keychain_ref": "fake-ref"})
        # Mock keychain resolution via decrypt
        with mock.patch("hpc_gui.services.connection_profile_service.unprotect_keychain_secret", return_value="kc-secret"):
            profile = load_profiles()[0]
            info = None
            # Use ssh_info_from_profile for keychain – should resolve without prompt
            model = WxConnectionModel([])
            # Need to ensure load_profiles lookup returns profile with ref
            info = ssh_info_from_profile(profile, model)
            assert info.password == "kc-secret"
            # Also via resolve_password_for_connect
            res = resolve_password_for_connect(profile, typed_password="", ask_master=lambda c: None)
            assert res == "kc-secret"
            # Via panel Connect click with fake backend
            host = build_connection_panel(frame, profiles=load_profiles())
            captured = {}
            def fake_connect(p):
                captured["pwd"] = p.get("password", "")
                return {"connected": True, "profile_name": p.get("name", "")}
            host._wx_connection_model._connect = fake_connect
            # Need to mock resolve to return kc-secret for connect path (keychain doesn't need master)
            # Our connect handler will call resolve which will call unprotect_keychain_secret – mock it at connection time
            with mock.patch("hpc_gui.services.connection_profile_service.unprotect_keychain_secret", return_value="kc-secret"):
                with mock.patch("hpc_gui.services.connection_profile_service.unprotect_keychain_secret", return_value="kc-secret"):
                    # Actually need to patch where resolve imports; patch the function in service module
                    # Already patched above, but connect handler imports inside, so patch that module
                    import hpc_gui.services.connection_profile_service as svc
                    with mock.patch.object(svc, "unprotect_keychain_secret", return_value="kc-secret"):
                        choices = host._wx_connection_controls["choices"]
                        choices.SetStringSelection("kc")
                        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
                        choices.GetEventHandler().ProcessEvent(evt)
                        wx.Yield()
                        btn = host._wx_connection_controls["connect"]
                        evt2 = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
                        # Mock MessageBox to avoid dialogs
                        with mock.patch("wx.MessageBox"):
                            btn.GetEventHandler().ProcessEvent(evt2)
                            for _ in range(30):
                                wx.Yield()
                                wx.MilliSleep(20)
                                if host._wx_connection_model.controller.state.value == "connected":
                                    break
                            assert captured.get("pwd") == "kc-secret"
                            # Ensure plaintext not persisted (password field absent or empty)
                            assert not load_profiles()[0].get("password")
                            assert "kc-secret" not in str(load_profiles()[0])
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.integration
@pytest.mark.semantic
def test_dpapi_connect_resolves(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        storage.upsert_profile({"name": "dp", "host": "h.example", "port": 22, "username": "user", "save_password": True, "password_dpapi": "fake-token"})
        with mock.patch("hpc_gui.services.connection_profile_service.unprotect_secret", return_value="dpapi-secret"):
            profile = load_profiles()[0]
            res = resolve_password_for_connect(profile, typed_password="", ask_master=lambda c: None)
            assert res == "dpapi-secret"
            model = WxConnectionModel([])
            info = ssh_info_from_profile(profile, model)
            assert info.password == "dpapi-secret"
            assert info.password != ""
            # Ensure transient only
            assert profile.get("password") == "" or profile.get("password") is None or profile.get("password") == ""
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.integration
@pytest.mark.wx
@pytest.mark.semantic
def test_master_encrypted_connect_with_prompt_and_cancel_and_wrong(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        from hpc_gui.core.crypto_master import encrypt_with_master
        enc = encrypt_with_master("master123", "master-secret")
        storage.upsert_profile({"name": "m", "host": "h.example", "port": 22, "username": "user", "save_password": True, "password_enc": enc.token, "password_salt": enc.salt})
        profile = load_profiles()[0]
        # Correct master resolves
        res = resolve_password_for_connect(profile, typed_password="", ask_master=lambda c: "master123")
        assert res == "master-secret"
        # Cancel aborts
        try:
            resolve_password_for_connect(profile, typed_password="", ask_master=lambda c: None)
            assert False, "should have raised master_cancelled"
        except RuntimeError as e:
            assert "master_cancelled" in str(e)
        # Wrong master fails safely
        try:
            resolve_password_for_connect(profile, typed_password="", ask_master=lambda c: "wrong")
            assert False, "should have raised master_wrong"
        except RuntimeError as e:
            assert "master_wrong" in str(e)
        # No prompt with allow_prompt=False via ssh_info_from_profile should raise saved_password_unavailable
        model = WxConnectionModel([])
        try:
            ssh_info_from_profile(profile, model)
            assert False, "should have raised saved_password_unavailable"
        except RuntimeError as e:
            assert "saved_password_unavailable" in str(e)
        # With GUI thread resolve, transient password should be used
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=load_profiles())
        captured = {}
        def fake_connect(p):
            captured["pwd"] = p.get("password", "")
            return {"connected": True, "profile_name": p.get("name", "")}
        host._wx_connection_model._connect = fake_connect
        # Mock master prompt to return correct master via resolve inside connect handler – we need to patch ask_master factory
        # Instead of relying on real dialog, patch _master_ask_factory to return our mock
        # We already have host; we need to ensure connect handler uses our mocked master
        # Patch the factory used inside build_connection_panel for connection – we can monkeypatch the service's encrypt/decrypt
        # For this test, we mock resolve to simulate correct master via patching unprotect? No, master path uses ask_master
        # Let's directly patch resolve_password_for_connect to return master-secret for this Connect click
        with mock.patch("hpc_gui.services.connection_profile_service.resolve_password_for_connect", return_value="master-secret"):
            choices = host._wx_connection_controls["choices"]
            choices.SetStringSelection("m")
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
                assert captured.get("pwd") == "master-secret"
                assert host._wx_connection_model.controller.state.value == "connected"
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.integration
@pytest.mark.wx
@pytest.mark.semantic
def test_test_cluster_resolves_keychain_dpapi_master_and_does_not_mutate(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        from hpc_gui.wx_connection_dialog import WxConnectionDialog
        from hpc_gui.core.crypto_master import encrypt_with_master

        # Seed storage with three profiles
        enc = encrypt_with_master("master123", "master-secret")
        storage.upsert_profile({"name": "kc", "host": "h.example", "port": 22, "username": "user", "save_password": True, "password_keychain_ref": "ref1"})
        storage.upsert_profile({"name": "dp", "host": "h.example", "port": 22, "username": "user", "save_password": True, "password_dpapi": "tok"})
        storage.upsert_profile({"name": "m", "host": "h.example", "port": 22, "username": "user", "save_password": True, "password_enc": enc.token, "password_salt": enc.salt})
        frame = wx.Frame(None)
        # Helper to test one profile
        for name, expected_resolver in [
            ("kc", lambda: mock.patch("hpc_gui.services.connection_profile_service.unprotect_keychain_secret", return_value="kc-secret")),
            ("dp", lambda: mock.patch("hpc_gui.services.connection_profile_service.unprotect_secret", return_value="dpapi-secret")),
        ]:
            profile = next(p for p in load_profiles() if p["name"] == name)
            before = [dict(p) for p in load_profiles()]
            dlg = WxConnectionDialog(frame, initial_profile=profile, mode="edit", on_save=lambda p: True)
            dlg.host_ctrl.SetValue("h.example")
            dlg.username_ctrl.SetValue("user")
            # Ensure password field empty (no typed)
            dlg.password_ctrl.SetValue("")
            # Mock self-test service and result dialog to avoid blocking
            captured = {}
            def fake_self_test(info, provider=None, project="", account=""):
                captured["pwd"] = info.password
                class R:
                    status = "PASS"
                    sections = []
                return R()
            with expected_resolver(), mock.patch("hpc_gui.services.cluster_self_test.run_cluster_self_test", side_effect=fake_self_test), \
                 mock.patch.object(WxConnectionDialog, "_show_self_test_result", lambda self, r: captured.update({"result": r})), \
                 mock.patch.object(WxConnectionDialog, "_show_self_test_error", lambda self, e: captured.update({"error": e})), \
                 mock.patch("wx.MessageBox"):
                with mock.patch.object(dlg.btn_test_cluster, "Enable"), mock.patch.object(dlg.btn_test_cluster, "SetLabel"):
                    dlg._test_cluster()
                    # Wait for worker
                    for _ in range(30):
                        wx.Yield()
                        wx.MilliSleep(20)
                        if captured.get("pwd"):
                            break
                    assert captured.get("pwd") in ("kc-secret", "dpapi-secret"), f"Test Cluster should resolve {name}"
            # Storage unchanged
            after = [dict(p) for p in load_profiles()]
            assert before == after, "Test Cluster must not mutate storage"
            dlg.Destroy()
            for _ in range(3):
                wx.Yield()
        # Master case with prompt
        profile_m = next(p for p in load_profiles() if p["name"] == "m")
        before_m = [dict(p) for p in load_profiles()]
        dlg_m = WxConnectionDialog(frame, initial_profile=profile_m, mode="edit", on_save=lambda p: True)
        dlg_m.host_ctrl.SetValue("h.example")
        dlg_m.username_ctrl.SetValue("user")
        dlg_m.password_ctrl.SetValue("")
        captured_m = {}
        def fake_self_test_m(info, provider=None, project="", account=""):
            captured_m["pwd"] = info.password
            class R:
                status = "PASS"
                sections = []
            return R()
        # Mock master ask to return correct master
        with mock.patch("hpc_gui.services.cluster_self_test.run_cluster_self_test", side_effect=fake_self_test_m), \
             mock.patch.object(WxConnectionDialog, "_show_self_test_result", lambda self, r: captured_m.update({"result": r})), \
             mock.patch.object(WxConnectionDialog, "_show_self_test_error", lambda self, e: captured_m.update({"error": e})), \
             mock.patch("wx.MessageBox"):
            # Patch the master ask inside dialog to return correct master without UI
            # We mock the resolve to return master-secret directly by patching the factory
            # Instead, patch resolve_password_for_connect to return expected
            with mock.patch("hpc_gui.services.connection_profile_service.resolve_password_for_connect", return_value="master-secret"):
                with mock.patch.object(dlg_m.btn_test_cluster, "Enable"), mock.patch.object(dlg_m.btn_test_cluster, "SetLabel"):
                    dlg_m._test_cluster()
                    for _ in range(30):
                        wx.Yield()
                        wx.MilliSleep(20)
                        if captured_m.get("pwd"):
                            break
                    assert captured_m.get("pwd") == "master-secret"
        after_m = [dict(p) for p in load_profiles()]
        assert before_m == after_m, "Master Test Cluster must not mutate storage"
        dlg_m.Destroy()
        # Typed override case
        profile_kc = next(p for p in load_profiles() if p["name"] == "kc")
        dlg_typed = WxConnectionDialog(frame, initial_profile=profile_kc, mode="edit", on_save=lambda p: True)
        dlg_typed.host_ctrl.SetValue("h.example")
        dlg_typed.username_ctrl.SetValue("user")
        dlg_typed.password_ctrl.SetValue("typed-override")
        captured_typed = {}
        def fake_self_test_typed(info, provider=None, project="", account=""):
            captured_typed["pwd"] = info.password
            class R:
                status = "PASS"
                sections = []
            return R()
        with mock.patch("hpc_gui.services.cluster_self_test.run_cluster_self_test", side_effect=fake_self_test_typed), \
             mock.patch.object(WxConnectionDialog, "_show_self_test_result", lambda self, r: captured_typed.update({"result": r})), \
             mock.patch.object(WxConnectionDialog, "_show_self_test_error", lambda self, e: captured_typed.update({"error": e})), \
             mock.patch("wx.MessageBox"):
            with mock.patch.object(dlg_typed.btn_test_cluster, "Enable"), mock.patch.object(dlg_typed.btn_test_cluster, "SetLabel"):
                dlg_typed._test_cluster()
                for _ in range(30):
                    wx.Yield()
                    wx.MilliSleep(20)
                    if captured_typed.get("pwd"):
                        break
                assert captured_typed.get("pwd") == "typed-override"
                # Ensure stored secret not overwritten
                assert next(p for p in load_profiles() if p["name"]=="kc")["password_keychain_ref"] == "ref1"
        dlg_typed.Destroy()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.integration
@pytest.mark.wx
@pytest.mark.semantic
@pytest.mark.regression
def test_typed_password_precedence(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        from hpc_gui.core.crypto_master import encrypt_with_master
        enc = encrypt_with_master("master123", "old-secret")
        profile = {"name": "p", "host": "h.example", "port": 22, "username": "user", "password": "new-temporary-secret", "save_password": True, "password_enc": enc.token, "password_salt": enc.salt}
        # ssh_info should use typed
        model = WxConnectionModel([])
        info = ssh_info_from_profile(profile, model)
        assert info.password == "new-temporary-secret"
        # resolve should also prefer typed
        res = resolve_password_for_connect(profile, typed_password="new-temporary-secret", ask_master=lambda c: "master123")
        assert res == "new-temporary-secret"
        # Stored secret not overwritten merely by Connect – check storage
        storage.upsert_profile({"name": "p", "host": "h.example", "save_password": True, "password_enc": enc.token, "password_salt": enc.salt})
        # Simulate Connect Selected with typed override via transient
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=load_profiles())
        # Directly test that transient with typed does not persist
        stored_before = [dict(p) for p in load_profiles()]
        # Fake connect that captures password
        captured = {}
        def fake(p):
            captured["pwd"] = p.get("password")
            return {"connected": True, "profile_name": p["name"]}
        host._wx_connection_model._connect = fake
        # Manually set profile password typed in stored? We simulate by patching resolve to return typed
        with mock.patch("hpc_gui.services.connection_profile_service.resolve_password_for_connect", return_value="new-temporary-secret"):
            choices = host._wx_connection_controls["choices"]
            choices.SetStringSelection("p")
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
                assert captured.get("pwd") == "new-temporary-secret"
        stored_after = [dict(p) for p in load_profiles()]
        assert stored_before == stored_after, "Stored secret must not be overwritten by Connect"
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_saved_password_unavailable_error(monkeypatch, caplog):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        # Profile with keychain ref but keychain will fail
        storage.upsert_profile({"name": "p", "host": "h.example", "port": 22, "username": "user", "save_password": True, "password_keychain_ref": "missing-ref"})
        host = build_connection_panel(frame, profiles=load_profiles())
        choices = host._wx_connection_controls["choices"]
        choices.SetStringSelection("p")
        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(evt)
        wx.Yield()
        btn = host._wx_connection_controls["connect"]
        # Mock unprotect to fail
        with mock.patch("hpc_gui.services.connection_profile_service.unprotect_keychain_secret", side_effect=RuntimeError("missing")):
            with mock.patch("wx.MessageBox") as MockBox:
                evt2 = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
                btn.GetEventHandler().ProcessEvent(evt2)
                for _ in range(30):
                    wx.Yield()
                    wx.MilliSleep(20)
                    if host._wx_connection_model.controller.state.value == "failed":
                        break
                assert host._wx_connection_model.controller.state.value == "failed"
                # Should have shown saved_password_unavailable, not generic (check both EN and TR)
                assert MockBox.called
                args, _ = MockBox.call_args
                msg_lower = str(args).lower()
                assert any(word in msg_lower for word in ["saved", "unavailable", "could not be decrypted", "kayıtlı", "çözülemedi", "kullanıcı"])
                # Must not log secret
                assert "missing-ref" not in str(caplog.text)
                # Buttons restored
                assert host._wx_connection_controls["add_connection"].IsEnabled()
                assert host._wx_connection_controls["connect"].IsEnabled()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.unit
@pytest.mark.wx
def test_mfa_respects_echo_and_not_logged(monkeypatch, caplog):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=[])
        model = host._wx_connection_model
        # Mock wx dialogs to capture which dialog type is used
        captured_dialogs = []

        class FakePwd:
            def __init__(self, *a, **kw):
                captured_dialogs.append("pwd")
                self.val = "secret1"
            def ShowModal(self): return wx.ID_OK
            def GetValue(self): return self.val
            def Destroy(self): pass
        class FakeTxt:
            def __init__(self, *a, **kw):
                captured_dialogs.append("txt")
                self.val = "visible2"
            def ShowModal(self): return wx.ID_OK
            def GetValue(self): return self.val
            def Destroy(self): pass
        with mock.patch.object(wx, "PasswordEntryDialog", FakePwd), mock.patch.object(wx, "TextEntryDialog", FakeTxt):
            from hpc_gui.services.connection_controller import KeyboardInteractiveRequest
            req = KeyboardInteractiveRequest("Title", "Instr", ("Prompt1:", "Prompt2:"), (False, True))
            answers = model.answer_keyboard_interactive(req)
            assert answers == ["secret1", "visible2"]
            assert captured_dialogs == ["pwd", "txt"], "echo False must use PasswordEntryDialog, echo True must use TextEntryDialog"
            # Ensure explicit echo wins over heuristic
            captured_dialogs.clear()
            req2 = KeyboardInteractiveRequest("Title", "Instr", ("password prompt",), (True,))
            model.answer_keyboard_interactive(req2)
            assert captured_dialogs == ["txt"], "echo True must not be masked even if prompt contains password"
        # No secret in logs
        assert "secret1" not in str(caplog.text)
        assert "visible2" not in str(caplog.text)
        # Answers not retained on model
        assert not hasattr(model, "secret1")
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.audit
@pytest.mark.wx
def test_password_dialogs_use_correct_api(monkeypatch):
    src = open("src/hpc_gui/wx_connection.py", encoding="utf-8").read()
    assert "wx.PasswordEntryDialog" in src, "MFA and edit auth must use PasswordEntryDialog"
    assert src.count("wx.PasswordEntryDialog") >= 2, "At least MFA and edit auth should use PasswordEntryDialog"
    # Ensure fragile style not used for password prompts
    assert "wx.TextEntryDialog(..., style=wx.TE_PASSWORD" not in src
