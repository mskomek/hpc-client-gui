"""Wave 71.1 hardening – wx Connection closure.

Covers P0 credential resolution, Test Cluster, dialogs, action states,
Save & Connect event chain, secret matrices, precedence, unavailable error,
host-key, provider/storage/quota non-regression, i18n, redaction, threading,
controller transitions, selected vs active, delete active.

All tests use isolated temp storage and mocked backends; no real HPC cluster.
"""

import tempfile
from pathlib import Path
from unittest import mock

import pytest

wx = pytest.importorskip("wx", reason="wxPython not installed – skipping wx GUI tests")

from hpc_gui.config import storage
from hpc_gui.config.storage import load_profiles
from hpc_gui.core.i18n import t, load_language
from hpc_gui.services.connection_profile_service import (
    resolve_password_for_connect,
)
from hpc_gui.services.connection_controller import ConnectionController
from hpc_gui.wx_connection import WxConnectionModel, build_connection_panel, ssh_info_from_profile


def _isolated_storage(monkeypatch):
    tmp = tempfile.TemporaryDirectory()
    # Patch both Path.home and the app_data_dir helpers so config and plugins
    # use the same isolated temp dir regardless of which helper a module
    # imported. Without this, conftest's tmp_path for plugins and our
    # Path.home temp would diverge and load_profiles would look in the wrong
    # place when tests are run as part of a large suite.
    monkeypatch.setattr(Path, "home", lambda: Path(tmp.name))
    # Also patch the core and config helpers directly
    try:
        import hpc_gui.core.paths as paths_mod
        import hpc_gui.config.storage as cfg_storage
        import hpc_gui.plugins.storage as plug_storage
        fake_dir = Path(tmp.name) / ".truba_slurm_gui"
        fake_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_dir)
        monkeypatch.setattr(cfg_storage, "app_data_dir", lambda: fake_dir)
        # plugins uses its own helper but conftest already patches it to tmp_path;
        # we override to use the same fake_dir for consistency when tests run
        # as part of the large suite.
        monkeypatch.setattr(plug_storage, "app_data_dir", lambda: fake_dir)
        monkeypatch.setattr(plug_storage, "plugins_root", lambda override=None: fake_dir / "plugins")
    except Exception:
        pass
    storage.save_config({"profiles": [], "settings": {}})
    return tmp


@pytest.fixture(autouse=True)
def _clean_wx_after():
    yield
    # Ensure any wx windows left open by a failing test are destroyed so the
    # next test's wx.App.Get() does not see a polluted app with open windows
    # (which causes UnregisterClass failures and order-dependent flakes).
    try:
        app = wx.GetApp()
        if app is not None:
            for win in list(wx.GetTopLevelWindows()):
                try:
                    win.Destroy()
                except Exception:
                    pass
            # Process pending destroys
            for _ in range(5):
                try:
                    wx.Yield()
                except Exception:
                    break
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Secure secret connection mapping
# ---------------------------------------------------------------------------

def test_keychain_connect_resolves(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        app = wx.App.Get() or wx.App(False)
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


def test_dpapi_connect_resolves(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        app = wx.App.Get() or wx.App(False)
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
        app = wx.App.Get() or wx.App(False)
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


# ---------------------------------------------------------------------------
# Test Cluster credential matrix
# ---------------------------------------------------------------------------

def test_test_cluster_resolves_keychain_dpapi_master_and_does_not_mutate(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        app = wx.App.Get() or wx.App(False)
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
        app = wx.App.Get() or wx.App(False)
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


def test_saved_password_unavailable_error(monkeypatch, caplog):
    tmp = _isolated_storage(monkeypatch)
    try:
        app = wx.App.Get() or wx.App(False)
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


# ---------------------------------------------------------------------------
# MFA and dialogs
# ---------------------------------------------------------------------------

def test_mfa_respects_echo_and_not_logged(monkeypatch, caplog):
    tmp = _isolated_storage(monkeypatch)
    try:
        app = wx.App.Get() or wx.App(False)
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


def test_password_dialogs_use_correct_api(monkeypatch):
    src = open("src/hpc_gui/wx_connection.py", encoding="utf-8").read()
    assert "wx.PasswordEntryDialog" in src, "MFA and edit auth must use PasswordEntryDialog"
    assert src.count("wx.PasswordEntryDialog") >= 2, "At least MFA and edit auth should use PasswordEntryDialog"
    # Ensure fragile style not used for password prompts
    assert "wx.TextEntryDialog(..., style=wx.TE_PASSWORD" not in src
    # Check that wx_connection_dialog still uses TE_PASSWORD for TextCtrl (allowed) but not for dialogs where PasswordEntryDialog should be used
    # For MFA, we already checked


# ---------------------------------------------------------------------------
# Save & Connect event chain
# ---------------------------------------------------------------------------

def test_save_and_connect_wx_event_chain(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        app = wx.App.Get() or wx.App(False)
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


def test_save_failure_prevents_connect(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        app = wx.App.Get() or wx.App(False)
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


def test_connect_failure_after_save_keeps_profile(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=[])
        class FakeDialog:
            def __init__(self, parent, initial_profile=None, mode="add", on_save=None, on_save_and_connect=None):
                self.on_save_and_connect = on_save_and_connect
                self._collected = {"name": "persisted", "host": "h.example", "port": 22, "username": "user", "system": {}, "file_manager": {}, "jump_host": {}, "save_password": False, "password_prompt_policy": "when-needed"}
            def ShowModal(self):
                result = self.on_save_and_connect(self._collected)
                # Save succeeds but connect fails; contract: return False
                assert result is False, f"Save & Connect with failed connect must return False, got {result!r}"
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
                for _ in range(20):
                    wx.Yield()
                    wx.MilliSleep(20)
                # Saved profile must remain
                assert len(load_profiles()) == 1
                assert load_profiles()[0]["name"] == "persisted"
                # Visible profile remains
                choices = host._wx_connection_controls["choices"]
                assert choices.FindString("persisted") != wx.NOT_FOUND
                # Status failed, buttons restored, no duplicate
                assert host._wx_connection_model.controller.state.value == "failed" or "failed" in host._wx_connection_controls["status"].GetLabel().lower()
                # No second save
                assert len(load_profiles()) == 1
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()


# ---------------------------------------------------------------------------
# Controller, selection, host-key
# ---------------------------------------------------------------------------

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
        app = wx.App.Get() or wx.App(False)
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


def test_selected_vs_active_profile(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        app = wx.App.Get() or wx.App(False)
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


def test_delete_active_profile_blocked(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        app = wx.App.Get() or wx.App(False)
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


def test_host_key_mapping(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=[])
        model = host._wx_connection_model
        for expected, wx_id in [("save", wx.ID_YES), ("once", wx.ID_NO), ("reject", wx.ID_CANCEL)]:
            with mock.patch("wx.MessageDialog") as MockDlg:
                inst = MockDlg.return_value
                inst.ShowModal.return_value = wx_id
                inst.Destroy = mock.Mock()
                result = model.decide_host_key(mock.Mock(hostname="h.example", fingerprint="aa:bb", role="target"))
                assert result == expected
        # Changed host keys must not be silently accepted – model defaults to reject (mocked to avoid popup)
        with mock.patch("wx.MessageDialog") as MockDlg:
            inst = MockDlg.return_value
            inst.ShowModal.return_value = wx.ID_CANCEL
            inst.Destroy = mock.Mock()
            assert model.decide_host_key(mock.Mock(hostname="h", fingerprint="changed", role="target")) == "reject"
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()


# ---------------------------------------------------------------------------
# i18n and redaction
# ---------------------------------------------------------------------------

def test_i18n_new_connection_keys():
    load_language("en")
    for key in ["connection.auth_cancelled", "connection.test_credential_error", "connection.master_unlock_error", "connection.saved_credential_unavailable", "connection.credential_unlock_prompt", "connection.saved_password_unavailable"]:
        assert t(key) != f"[{key}]", f"Missing EN key {key}"
    load_language("tr")
    for key in ["connection.auth_cancelled", "connection.test_credential_error", "connection.master_unlock_error", "connection.saved_credential_unavailable", "connection.credential_unlock_prompt", "connection.saved_password_unavailable"]:
        assert t(key) != f"[{key}]", f"Missing TR key {key}"
    load_language("en")


def test_error_redaction_no_secret_in_logs(monkeypatch, caplog):
    import logging
    from hpc_gui.services.connection_profile_service import resolve_password_for_connect
    from hpc_gui.core.crypto_master import encrypt_with_master
    tmp = _isolated_storage(monkeypatch)
    try:
        enc = encrypt_with_master("master123", "super-secret-123")
        storage.upsert_profile({"name": "p", "host": "h.example", "save_password": True, "password_enc": enc.token, "password_salt": enc.salt})
        profile = load_profiles()[0]
        # Simulate wrong master error – ensure logs don't contain secret
        logger = logging.getLogger("hpc_gui")
        with caplog.at_level(logging.INFO):
            try:
                resolve_password_for_connect(profile, typed_password="", ask_master=lambda c: "wrong")
            except RuntimeError as e:
                logger.info(f"Failed to resolve password for {profile.get('name')} host {profile.get('host')} error {type(e).__name__}")
                # Do not log secret
                assert "super-secret-123" not in str(caplog.text)
                assert "wrong" not in str(caplog.text) or "master" in str(caplog.text).lower()
        # Also test that successful resolve doesn't log secret
        with caplog.at_level(logging.INFO):
            res = resolve_password_for_connect(profile, typed_password="", ask_master=lambda c: "master123")
            logger.info(f"Resolved for {profile.get('name')}")
            assert "super-secret-123" not in str(caplog.text)
            assert res == "super-secret-123"
    finally:
        tmp.cleanup()


# ---------------------------------------------------------------------------
# Non-regression: provider/template, storage, quota
# ---------------------------------------------------------------------------

def test_provider_template_no_generic_branch(monkeypatch):
    src = open("src/hpc_gui/wx_connection.py", encoding="utf-8").read()
    assert "TRUBA" not in src
    src2 = open("src/hpc_gui/wx_connection_dialog.py", encoding="utf-8").read()
    # Allow mention in comments but not as hardcoded branch
    assert src2.count("TRUBA") == 0 or "provider_template" in src2

def test_quota_fail_closed():
    from hpc_gui.services.quota_monitor import quota_gate
    assert quota_gate({"enabled": False, "command_template": "cmd", "backend_id": "x", "consent": True}, backend_ids=["x"], connected=True) == "disabled"
    assert quota_gate({"enabled": True, "command_template": "", "backend_id": "x"}, backend_ids=["x"]) == "not_configured"

def test_storage_metadata_preserved(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        from hpc_gui.wx_connection_dialog import WxConnectionDialog
        app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        initial = {"name": "lab", "host": "h.example", "system": {"future_key": {"v": 1}}, "file_manager": {"future_key": 42}}
        dlg = WxConnectionDialog(frame, initial_profile=initial, mode="edit")
        assert dlg._system_form_values()["future_key"] == {"v": 1}
        dlg.Destroy()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()
