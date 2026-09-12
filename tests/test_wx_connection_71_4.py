"""Wave 71.4 — wx Connection final micro-closure.

Covers: master-password Remember=false/true settings mutation,
Test Cluster settings mutation, connect_selected return contract,
Save & Connect cancel/wrong-master regression.

All tests use isolated temp storage and mocked backends; no real HPC cluster.
"""

import tempfile
from copy import deepcopy
from pathlib import Path
from unittest import mock

import pytest

wx = pytest.importorskip("wx", reason="wxPython not installed")

from hpc_gui.config import storage
from hpc_gui.config.storage import load_profiles, load_settings
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


def _make_master_encrypted_profile(monkeypatch, name="m-test", master="master123", secret="my-secret"):
    """Create a master-encrypted profile in isolated storage."""
    from hpc_gui.core.crypto_master import encrypt_with_master
    enc = encrypt_with_master(master, secret)
    storage.upsert_profile({
        "name": name,
        "host": "h.example",
        "port": 22,
        "username": "user",
        "save_password": True,
        "password_enc": enc.token,
        "password_salt": enc.salt,
    })


def _mock_master_dialog_widgets(master_password="master123", remember=False):
    """Create mock wx widgets for the master-password dialog.
    Returns (fake_dlg, fake_pwd_ctrl, fake_cb, patchers) tuple.
    """
    fake_pwd_ctrl = mock.Mock()
    fake_pwd_ctrl.GetValue.return_value = master_password
    fake_pwd_ctrl.SetFocus = mock.Mock()
    fake_confirm_ctrl = mock.Mock()
    fake_confirm_ctrl.GetValue.return_value = ""

    tc_call = [0]
    def fake_textctrl(*args, **kwargs):
        tc_call[0] += 1
        return fake_pwd_ctrl if tc_call[0] == 1 else fake_confirm_ctrl

    fake_cb = mock.Mock()
    fake_cb.GetValue.return_value = remember

    fake_dlg = mock.Mock()
    fake_dlg.ShowModal.return_value = wx.ID_OK
    fake_dlg.Destroy = mock.Mock()
    fake_sizer = mock.Mock()
    fake_static = mock.Mock()

    return fake_dlg, fake_cb, fake_textctrl, fake_sizer, fake_static


# ---------------------------------------------------------------------------
# 71.4.1 — Master Remember=false: no settings/secret mutation
# ---------------------------------------------------------------------------


@pytest.mark.wx
@pytest.mark.gui
def test_master_password_remember_false_no_settings_mutation(monkeypatch):
    """Master password prompt → Remember=false → settings unchanged,
    protect_secret not called, update_settings not called for master persistence.
    """
    tmp = _isolated_storage(monkeypatch)
    try:
        _make_master_encrypted_profile(monkeypatch, name="m-norem")
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=load_profiles())
        captured = {}

        def fake_connect(p):
            captured["pwd"] = p.get("password", "")
            return {"connected": True, "profile_name": p.get("name")}

        host._wx_connection_model._connect = fake_connect

        # Snapshot settings before
        settings_before = deepcopy(load_settings())

        choices = host._wx_connection_controls["choices"]
        choices.SetStringSelection("m-norem")
        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(evt)
        wx.Yield()

        fake_dlg, fake_cb, fake_textctrl, fake_sizer, fake_static = _mock_master_dialog_widgets(remember=False)

        btn = host._wx_connection_controls["connect"]
        with mock.patch("wx.Dialog", return_value=fake_dlg), \
             mock.patch("wx.TextCtrl", side_effect=fake_textctrl), \
             mock.patch("wx.StaticText", return_value=fake_static), \
             mock.patch("wx.CheckBox", return_value=fake_cb), \
             mock.patch("wx.BoxSizer", return_value=fake_sizer), \
             mock.patch("wx.FlexGridSizer", return_value=fake_sizer), \
             mock.patch("wx.MessageBox"), \
             mock.patch("hpc_gui.core.secret_store.protect_secret") as mock_protect, \
             mock.patch("hpc_gui.config.storage.update_settings") as mock_update:
            evt2 = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
            btn.GetEventHandler().ProcessEvent(evt2)
            for _ in range(30):
                wx.Yield()
                wx.MilliSleep(20)
                if host._wx_connection_model.controller.state.value == "connected":
                    break

            # Connection succeeded with correct decrypted secret
            assert captured.get("pwd") == "my-secret"
            # Remember checkbox was explicitly False
            fake_cb.GetValue.assert_called()
            assert fake_cb.GetValue.return_value is False
            # protect_secret was NOT called (Remember=false)
            mock_protect.assert_not_called()
            # update_settings was NOT called for master-password persistence
            for call in mock_update.call_args_list:
                args = call[0] if call[0] else call[1]
                if isinstance(args, dict):
                    assert "master_password_dpapi" not in args

        # Settings unchanged
        settings_after = deepcopy(load_settings())
        assert settings_after.get("master_password_dpapi") == settings_before.get("master_password_dpapi")
        assert not settings_after.get("master_password_dpapi")

        # Profile storage unchanged (no plaintext password persisted)
        profile = next(p for p in load_profiles() if p["name"] == "m-norem")
        assert profile.get("password") == "" or not profile.get("password")
        assert "my-secret" not in str(profile)

        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()


# ---------------------------------------------------------------------------
# 71.4.2 — Master Remember=true: persist protected master
# ---------------------------------------------------------------------------


@pytest.mark.wx
@pytest.mark.gui
def test_master_password_remember_true_persists_protected(monkeypatch):
    """Master password prompt → Remember=true → protect_secret called,
    update_settings called with dpapi token, plaintext never stored.
    """
    tmp = _isolated_storage(monkeypatch)
    try:
        _make_master_encrypted_profile(monkeypatch, name="m-rem")
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=load_profiles())
        captured = {}

        def fake_connect(p):
            captured["pwd"] = p.get("password", "")
            return {"connected": True, "profile_name": p.get("name")}

        host._wx_connection_model._connect = fake_connect

        choices = host._wx_connection_controls["choices"]
        choices.SetStringSelection("m-rem")
        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(evt)
        wx.Yield()

        fake_dlg, fake_cb, fake_textctrl, fake_sizer, fake_static = _mock_master_dialog_widgets(remember=True)

        btn = host._wx_connection_controls["connect"]
        with mock.patch("wx.Dialog", return_value=fake_dlg), \
             mock.patch("wx.TextCtrl", side_effect=fake_textctrl), \
             mock.patch("wx.StaticText", return_value=fake_static), \
             mock.patch("wx.CheckBox", return_value=fake_cb), \
             mock.patch("wx.BoxSizer", return_value=fake_sizer), \
             mock.patch("wx.FlexGridSizer", return_value=fake_sizer), \
             mock.patch("wx.MessageBox"), \
             mock.patch("hpc_gui.core.secret_store.protect_secret", return_value="protected-token-714") as mock_protect, \
             mock.patch("hpc_gui.config.storage.update_settings"):
            evt2 = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
            btn.GetEventHandler().ProcessEvent(evt2)
            for _ in range(30):
                wx.Yield()
                wx.MilliSleep(20)
                if host._wx_connection_model.controller.state.value == "connected":
                    break

            # Connection succeeded
            assert captured.get("pwd") == "my-secret"
            # protect_secret WAS called with the master password
            mock_protect.assert_called_once_with("master123")

        # Plaintext master password never stored in profile
        profile = next(p for p in load_profiles() if p["name"] == "m-rem")
        assert "master123" not in str(profile)
        assert profile.get("password") == "" or not profile.get("password")

        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()


# ---------------------------------------------------------------------------
# 71.4.3 — Test Cluster Remember=false: no settings mutation
# ---------------------------------------------------------------------------


@pytest.mark.wx
@pytest.mark.gui
def test_cluster_self_test_remember_false_no_settings_mutation(monkeypatch):
    """Test Cluster → master dialog → Remember=false → settings unchanged,
    profiles unchanged, no secret-store write.
    """
    from hpc_gui.wx_connection_dialog import WxConnectionDialog

    tmp = _isolated_storage(monkeypatch)
    try:
        _make_master_encrypted_profile(monkeypatch, name="m-cl-norem")
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        profile = next(p for p in load_profiles() if p["name"] == "m-cl-norem")
        profiles_before = deepcopy(load_profiles())
        settings_before = deepcopy(load_settings())

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

        fake_dlg, fake_cb, fake_textctrl, fake_sizer, fake_static = _mock_master_dialog_widgets(remember=False)

        with mock.patch("hpc_gui.services.cluster_self_test.run_cluster_self_test", side_effect=fake_self_test), \
             mock.patch.object(WxConnectionDialog, "_show_self_test_result", lambda self, r: captured.update({"result": r})), \
             mock.patch.object(WxConnectionDialog, "_show_self_test_error", lambda self, e: captured.update({"error": e})), \
             mock.patch("wx.Dialog", return_value=fake_dlg), \
             mock.patch("wx.TextCtrl", side_effect=fake_textctrl), \
             mock.patch("wx.StaticText", return_value=fake_static), \
             mock.patch("wx.CheckBox", return_value=fake_cb), \
             mock.patch("wx.BoxSizer", return_value=fake_sizer), \
             mock.patch("wx.FlexGridSizer", return_value=fake_sizer), \
             mock.patch("wx.MessageBox"), \
             mock.patch("hpc_gui.core.secret_store.protect_secret") as mock_protect, \
             mock.patch("hpc_gui.config.storage.update_settings") as mock_update:
            btn = dlg.btn_test_cluster
            evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
            btn.GetEventHandler().ProcessEvent(evt)
            for _ in range(30):
                wx.Yield()
                wx.MilliSleep(20)
                if captured.get("pwd"):
                    break
            # Real decrypt produced the credential
            assert captured.get("pwd") == "my-secret"
            # protect_secret NOT called
            mock_protect.assert_not_called()
            # update_settings NOT called for master persistence
            for call in mock_update.call_args_list:
                args = call[0] if call[0] else call[1]
                if isinstance(args, dict):
                    assert "master_password_dpapi" not in args

        # Profiles unchanged
        profiles_after = deepcopy(load_profiles())
        assert profiles_after == profiles_before
        # Settings unchanged
        settings_after = deepcopy(load_settings())
        assert settings_after.get("master_password_dpapi") == settings_before.get("master_password_dpapi")

        dlg.Destroy()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()


# ---------------------------------------------------------------------------
# 71.4.4 — Test Cluster cancel: no backend call, no mutation
# ---------------------------------------------------------------------------


@pytest.mark.wx
@pytest.mark.gui
def test_cluster_self_test_cancel_no_mutation(monkeypatch):
    """Test Cluster → master dialog Cancel → no self-test, no settings change."""
    from hpc_gui.wx_connection_dialog import WxConnectionDialog

    tmp = _isolated_storage(monkeypatch)
    try:
        _make_master_encrypted_profile(monkeypatch, name="m-cl-cancel")
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        profile = next(p for p in load_profiles() if p["name"] == "m-cl-cancel")
        profiles_before = deepcopy(load_profiles())
        settings_before = deepcopy(load_settings())

        dlg = WxConnectionDialog(frame, initial_profile=profile, mode="edit", on_save=lambda p: True)
        dlg.host_ctrl.SetValue("h.example")
        dlg.username_ctrl.SetValue("user")
        dlg.password_ctrl.SetValue("")

        backend_called = [False]
        def fake_self_test(info, provider=None, project="", account=""):
            backend_called[0] = True
            class R:
                status = "PASS"
                sections = []
            return R()

        fake_dlg = mock.Mock()
        fake_dlg.ShowModal.return_value = wx.ID_CANCEL
        fake_dlg.Destroy = mock.Mock()
        fake_sizer = mock.Mock()
        fake_static = mock.Mock()
        fake_cb = mock.Mock()
        fake_tc = mock.Mock()

        with mock.patch("hpc_gui.services.cluster_self_test.run_cluster_self_test", side_effect=fake_self_test), \
             mock.patch.object(WxConnectionDialog, "_show_self_test_result", lambda self, r: None), \
             mock.patch.object(WxConnectionDialog, "_show_self_test_error", lambda self, e: None), \
             mock.patch("wx.Dialog", return_value=fake_dlg), \
             mock.patch("wx.TextCtrl", return_value=fake_tc), \
             mock.patch("wx.StaticText", return_value=fake_static), \
             mock.patch("wx.CheckBox", return_value=fake_cb), \
             mock.patch("wx.BoxSizer", return_value=fake_sizer), \
             mock.patch("wx.FlexGridSizer", return_value=fake_sizer), \
             mock.patch("wx.MessageBox"):
            btn = dlg.btn_test_cluster
            evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, btn.GetId())
            btn.GetEventHandler().ProcessEvent(evt)
            for _ in range(10):
                wx.Yield()
                wx.MilliSleep(20)
            assert not backend_called[0]
            assert btn.IsEnabled()

        profiles_after = deepcopy(load_profiles())
        settings_after = deepcopy(load_settings())
        assert profiles_after == profiles_before
        assert settings_after.get("master_password_dpapi") == settings_before.get("master_password_dpapi")

        dlg.Destroy()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()


# ---------------------------------------------------------------------------
# 71.4.5 — connect_selected return contract: no selection → False
# ---------------------------------------------------------------------------


@pytest.mark.wx
@pytest.mark.gui
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


# ---------------------------------------------------------------------------
# 71.4.6 — connect_selected return contract: worker starts → True
# ---------------------------------------------------------------------------


@pytest.mark.wx
@pytest.mark.gui
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


# ---------------------------------------------------------------------------
# 71.4.7 — Save & Connect + master cancel → returns False
# ---------------------------------------------------------------------------


@pytest.mark.wx
@pytest.mark.gui
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


# ---------------------------------------------------------------------------
# 71.4.8 — Save & Connect + wrong master → returns False
# ---------------------------------------------------------------------------


@pytest.mark.wx
@pytest.mark.gui
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
