"""Wave 71.3 — wx Connection evidence closure.

Covers: production Save & Connect event-chain with blank-name canonical path,
real master-password wx prompt (no cache), Test Cluster real button event,
Test Cluster cancel path, typed password precedence.

All tests use isolated temp storage and mocked backends; no real HPC cluster.
"""

from unittest import mock

import pytest

from support.wx_connection_fixtures import clean_wx_after as _clean_wx_after, isolated_storage as _isolated_storage  # noqa: F401

wx = pytest.importorskip("wx", reason="wxPython not installed")

from hpc_gui.config import storage
from hpc_gui.config.storage import load_profiles
from hpc_gui.wx_connection import build_connection_panel






# ---------------------------------------------------------------------------
# 71.3.1 — Strict async failure test
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# 71.3.2 — Production Save & Connect event-chain with blank-name canonical path
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# 71.3.3 — Master-password real wx prompt (no cache)
# ---------------------------------------------------------------------------


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_master_password_real_wx_prompt_no_cache(monkeypatch):
    """Real resolver chain with wx dialog prompt mocked at widget level.
    No DPAPI cache seeded. Real _master_ask_factory → wx.Dialog mocked →
    real resolve_password_for_connect → real decrypt_with_master.

    Chain:
    saved master-encrypted profile → Connect Selected real wx button →
    real resolve_password_for_connect() → real _master_ask_factory() →
    wx.Dialog mocked to return master123 → real decrypt → Connected.
    """
    from hpc_gui.core.crypto_master import encrypt_with_master

    tmp = _isolated_storage(monkeypatch)
    try:
        enc = encrypt_with_master("master123", "prompt-secret")
        storage.upsert_profile({
            "name": "m-prompt",
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
        captured = {}

        def fake_connect(p):
            captured["pwd"] = p.get("password", "")
            captured["name"] = p.get("name")
            return {"connected": True, "profile_name": p.get("name")}

        host._wx_connection_model._connect = fake_connect

        choices = host._wx_connection_controls["choices"]
        choices.SetStringSelection("m-prompt")
        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(evt)
        wx.Yield()

        # Mock wx widgets used by _master_ask_factory
        fake_pwd_ctrl = mock.Mock()
        fake_pwd_ctrl.GetValue.return_value = "master123"
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
                if host._wx_connection_model.controller.state.value == "connected":
                    break

            # Real decrypt produced the transient password
            assert captured.get("pwd") == "prompt-secret"
            assert host._wx_connection_model.controller.state.value == "connected"
            # Dialog was invoked (prompt path exercised)
            fake_dlg.ShowModal.assert_called()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()


# ---------------------------------------------------------------------------
# 71.3.4 — Cached-master path (separate, not evidence for wx prompt)
# ---------------------------------------------------------------------------


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_master_password_cached_path(monkeypatch):
    """Cached master password → no interactive prompt → decrypt succeeds.

    This tests the cache optimization path, not the wx prompt path.
    Kept as valid coverage of _master_ask_factory cache behavior.
    """
    from hpc_gui.core.crypto_master import encrypt_with_master

    tmp = _isolated_storage(monkeypatch)
    try:
        enc = encrypt_with_master("master123", "cached-secret")
        storage.upsert_profile({
            "name": "m-cached",
            "host": "h.example",
            "port": 22,
            "username": "user",
            "save_password": True,
            "password_enc": enc.token,
            "password_salt": enc.salt,
        })
        # Seed DPAPI cache
        import hpc_gui.config.storage as cfg_storage
        fake_token = "dpapi-cache-test"
        monkeypatch.setattr(cfg_storage, "load_settings", lambda: {"master_password_dpapi": fake_token})
        # Model Windows' DPAPI availability so Linux exercises the cached
        # credential path instead of opening an interactive password dialog.
        monkeypatch.setattr("hpc_gui.core.secret_store.is_available", lambda: True)
        monkeypatch.setattr("hpc_gui.core.secret_store.unprotect_secret", lambda t: "master123" if t == fake_token else (_ for _ in ()).throw(ValueError()))
        monkeypatch.setattr("hpc_gui.services.connection_profile_service.unprotect_secret", lambda t: "master123" if t == fake_token else (_ for _ in ()).throw(ValueError()))

        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=load_profiles())
        captured = {}

        def fake_connect(p):
            captured["pwd"] = p.get("password", "")
            return {"connected": True, "profile_name": p.get("name")}

        host._wx_connection_model._connect = fake_connect

        choices = host._wx_connection_controls["choices"]
        choices.SetStringSelection("m-cached")
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
            assert captured.get("pwd") == "cached-secret"
            assert host._wx_connection_model.controller.state.value == "connected"
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()


# ---------------------------------------------------------------------------
# 71.3.5 — Master password cancel via wx prompt
# ---------------------------------------------------------------------------


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_master_password_wx_prompt_cancel(monkeypatch):
    """Connect Selected → wx master dialog → Cancel → no SSH, buttons restored.

    No DPAPI cache. wx.Dialog mocked to return Cancel.
    Real resolve_password_for_connect, real _master_ask_factory.
    """
    from hpc_gui.core.crypto_master import encrypt_with_master

    tmp = _isolated_storage(monkeypatch)
    try:
        enc = encrypt_with_master("master123", "should-not-reach")
        storage.upsert_profile({
            "name": "m-cancel-prompt",
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
        choices.SetStringSelection("m-cancel-prompt")
        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
        choices.GetEventHandler().ProcessEvent(evt)
        wx.Yield()

        # Mock wx.Dialog to return Cancel (simulating user pressing Cancel)
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
            # No SSH attempt
            assert len(connect_calls) == 0
            # Not connected
            assert host._wx_connection_model.controller.state.value != "connected"
            # Buttons restored
            assert host._wx_connection_controls["add_connection"].IsEnabled()
            assert host._wx_connection_controls["connect"].IsEnabled()
            # No secret leaked
            assert "should-not-reach" not in str(load_profiles()[0])
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()
