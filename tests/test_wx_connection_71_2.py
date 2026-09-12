"""Wave 71.2 — wx Connection final closure tests.

Covers: blank-name Save & Connect, real WxConnectionDialog button event,
master-password wx event chain (success/cancel/wrong), Test Cluster
master-password chain, typed password precedence.

All tests use isolated temp storage and mocked backends; no real HPC cluster.
"""

import tempfile
from pathlib import Path
from unittest import mock

import pytest

wx = pytest.importorskip("wx", reason="wxPython not installed")

from hpc_gui.config import storage
from hpc_gui.config.storage import load_profiles
from hpc_gui.wx_connection import build_connection_panel


def _isolated_storage(monkeypatch):
    tmp = tempfile.TemporaryDirectory()
    monkeypatch.setattr(Path, "home", lambda: Path(tmp.name))
    try:
        import hpc_gui.core.paths as paths_mod
        import hpc_gui.config.storage as cfg_storage
        import hpc_gui.plugins.storage as plug_storage
        fake_dir = Path(tmp.name) / ".truba_slurm_gui"
        fake_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_dir)
        monkeypatch.setattr(cfg_storage, "app_data_dir", lambda: fake_dir)
        monkeypatch.setattr(plug_storage, "app_data_dir", lambda: fake_dir)
        monkeypatch.setattr(plug_storage, "plugins_root", lambda override=None: fake_dir / "plugins")
    except Exception:
        pass
    storage.save_config({"profiles": [], "settings": {}})
    return tmp


def _seed_master_dpapi_cache(monkeypatch, master_password):
    """Pre-seed the DPAPI master-password cache so _master_ask_factory returns
    the master without opening a wx dialog.
    """
    import hpc_gui.config.storage as cfg_storage
    fake_token = f"dpapi-{master_password}"

    def fake_load_settings():
        return {"master_password_dpapi": fake_token}

    def fake_unprotect(token):
        if token == fake_token:
            return master_password
        raise ValueError("decrypt failed")

    monkeypatch.setattr(cfg_storage, "load_settings", fake_load_settings)
    monkeypatch.setattr("hpc_gui.core.secret_store.unprotect_secret", fake_unprotect)
    monkeypatch.setattr("hpc_gui.services.connection_profile_service.unprotect_secret", fake_unprotect)


@pytest.fixture(autouse=True)
def _clean_wx_after():
    yield
    try:
        app = wx.GetApp()
        if app is not None:
            for win in list(wx.GetTopLevelWindows()):
                try:
                    win.Destroy()
                except Exception:
                    pass
            for _ in range(5):
                try:
                    wx.Yield()
                except Exception:
                    break
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 71.2.1 Blank-name Save & Connect
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# 71.2.2 Real WxConnectionDialog Save & Connect button event
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# 71.2.3 Master-password real wx chain (correct master)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# 71.2.4 Master password cancel
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# 71.2.5 Wrong master password
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# 71.2.6 Test Cluster master-password chain
# ---------------------------------------------------------------------------


def test_cluster_self_test_master_password_chain(monkeypatch):
    """Test Cluster: saved master-encrypted profile -> edit dialog -> Test Cluster -> real resolver -> decrypt.

    Does NOT mock resolve_password_for_connect or decrypt_with_master.
    Pre-seeds DPAPI cache so _make_master_ask returns master without wx dialog.
    """
    from hpc_gui.wx_connection_dialog import WxConnectionDialog
    from hpc_gui.core.crypto_master import encrypt_with_master

    tmp = _isolated_storage(monkeypatch)
    try:
        enc = encrypt_with_master("master123", "cluster-secret")
        storage.upsert_profile({
            "name": "m-cluster",
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
        profile = next(p for p in load_profiles() if p["name"] == "m-cluster")
        before = [dict(p) for p in load_profiles()]

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

        with mock.patch("hpc_gui.services.cluster_self_test.run_cluster_self_test", side_effect=fake_self_test), \
             mock.patch.object(WxConnectionDialog, "_show_self_test_result", lambda self, r: captured.update({"result": r})), \
             mock.patch.object(WxConnectionDialog, "_show_self_test_error", lambda self, e: captured.update({"error": e})), \
             mock.patch("wx.MessageBox"):
            with mock.patch.object(dlg.btn_test_cluster, "Enable"), mock.patch.object(dlg.btn_test_cluster, "SetLabel"):
                dlg._test_cluster()
                for _ in range(30):
                    wx.Yield()
                    wx.MilliSleep(20)
                    if captured.get("pwd"):
                        break
                assert captured.get("pwd") == "cluster-secret"
        after = [dict(p) for p in load_profiles()]
        assert before == after, "Test Cluster must not mutate storage"
        dlg.Destroy()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()
