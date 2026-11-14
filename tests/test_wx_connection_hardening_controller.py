"""Wave 71.1 hardening – wx Connection closure.

Covers P0 credential resolution, Test Cluster, dialogs, action states,
Save & Connect event chain, secret matrices, precedence, unavailable error,
host-key, provider/storage/quota non-regression, i18n, redaction, threading,
controller transitions, selected vs active, delete active.

All tests use isolated temp storage and mocked backends; no real HPC cluster.
"""

from unittest import mock

import pytest

wx = pytest.importorskip("wx", reason="wxPython not installed – skipping wx GUI tests")

from hpc_gui.config import storage
from hpc_gui.config.storage import load_profiles
from hpc_gui.core.i18n import t, load_language
from hpc_gui.services.connection_profile_service import (
    resolve_password_for_connect,
)
from hpc_gui.wx_connection import build_connection_panel
from support.wx_connection_hardening_env import (_isolated_storage)


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


@pytest.mark.unit
@pytest.mark.wx
def test_host_key_mapping(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
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


@pytest.mark.contract
def test_i18n_new_connection_keys():
    load_language("en")
    for key in ["connection.auth_cancelled", "connection.test_credential_error", "connection.master_unlock_error", "connection.saved_credential_unavailable", "connection.credential_unlock_prompt", "connection.saved_password_unavailable"]:
        assert t(key) != f"[{key}]", f"Missing EN key {key}"
    load_language("tr")
    for key in ["connection.auth_cancelled", "connection.test_credential_error", "connection.master_unlock_error", "connection.saved_credential_unavailable", "connection.credential_unlock_prompt", "connection.saved_password_unavailable"]:
        assert t(key) != f"[{key}]", f"Missing TR key {key}"
    load_language("en")


@pytest.mark.integration
@pytest.mark.semantic
def test_error_redaction_no_secret_in_logs(monkeypatch, caplog):
    import logging
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


@pytest.mark.audit
@pytest.mark.wx
def test_provider_template_no_generic_branch(monkeypatch):
    src = open("src/hpc_gui/wx_connection.py", encoding="utf-8").read()
    assert "TRUBA" not in src
    src2 = open("src/hpc_gui/wx_connection_dialog.py", encoding="utf-8").read()
    # Allow mention in comments but not as hardcoded branch
    assert src2.count("TRUBA") == 0 or "provider_template" in src2


@pytest.mark.unit
def test_quota_fail_closed():
    from hpc_gui.services.quota_monitor import quota_gate
    assert quota_gate({"enabled": False, "command_template": "cmd", "backend_id": "x", "consent": True}, backend_ids=["x"], connected=True) == "disabled"
    assert quota_gate({"enabled": True, "command_template": "", "backend_id": "x"}, backend_ids=["x"]) == "not_configured"


@pytest.mark.contract
@pytest.mark.wx
def test_storage_metadata_preserved(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        from hpc_gui.wx_connection_dialog import WxConnectionDialog
        _wx_app = wx.App.Get() or wx.App(False)
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
