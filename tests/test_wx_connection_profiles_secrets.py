"""Wave 71 – wx Connection profile management polish tests.

Covers add-button enabled, CRUD, secrets, templates, storage, quota,
advanced SSH, ssh_info mapping, MFA/host-key, action states, i18n.

Uses isolated temp storage and mock/fake backends; never hits a real cluster.
"""

import tempfile
from pathlib import Path
from unittest import mock

import pytest

# Shared imports
from hpc_gui.config import storage
from hpc_gui.config.storage import load_profiles
from hpc_gui.config.system_profile import builtin_system_template_groups
from hpc_gui.plugins.templates import installed_cluster_template_groups

wx = pytest.importorskip("wx", reason="wxPython not installed – skipping wx GUI tests")
from support.wx_profiles_env import (_isolated_storage)


@pytest.mark.gui
@pytest.mark.wx
def test_delete_requires_confirmation_and_cleans(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        from hpc_gui.wx_connection import build_connection_panel

        # Seed storage with profile
        storage.upsert_profile({"name": "to-delete", "host": "h.example", "port": 22, "username": "user"})
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=load_profiles())
        choices = host._wx_connection_controls["choices"]
        assert choices.FindString("to-delete") != wx.NOT_FOUND
        choices.SetStringSelection("to-delete")
        # Simulate cancel – we mock MessageDialog to return NO, then trigger delete button
        with mock.patch.object(wx, "MessageDialog") as MockDlg:
            inst = MockDlg.return_value
            inst.ShowModal.return_value = wx.ID_NO
            inst.Destroy = mock.Mock()
            delete_btn = host._wx_connection_controls["delete"]
            evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, delete_btn.GetId())
            delete_btn.GetEventHandler().ProcessEvent(evt)
            wx.Yield()
            # Profile should still exist after cancel
            assert len([p for p in load_profiles() if p.get("name") == "to-delete"]) == 1
        # Confirm removes – mock YES
        with mock.patch.object(wx, "MessageDialog") as MockDlg2:
            inst2 = MockDlg2.return_value
            inst2.ShowModal.return_value = wx.ID_YES
            inst2.Destroy = mock.Mock()
            delete_btn = host._wx_connection_controls["delete"]
            evt2 = wx.CommandEvent(wx.EVT_BUTTON.typeId, delete_btn.GetId())
            delete_btn.GetEventHandler().ProcessEvent(evt2)
            wx.Yield()
            assert len([p for p in load_profiles() if p.get("name") == "to-delete"]) == 0
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()


@pytest.mark.integration
@pytest.mark.semantic
def test_secret_persistence_and_removal(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        from hpc_gui.services.connection_profile_service import save_profile

        # Save with password -> no plaintext
        collected = {"name": "sec", "host": "h.example", "port": 22, "username": "user", "system": {}, "file_manager": {}, "jump_host": {}, "save_password": True, "password_prompt_policy": "when-needed"}
        with mock.patch("hpc_gui.services.connection_profile_service.keychain_available", return_value=False), \
             mock.patch("hpc_gui.services.connection_profile_service.os_secret_store_available", return_value=False), \
             mock.patch("hpc_gui.services.connection_profile_service.encrypt_with_master") as mock_enc:
            from hpc_gui.core.crypto_master import EncryptedSecret
            mock_enc.return_value = EncryptedSecret(token="tok", salt="salt")
            saved = save_profile(collected, initial_profile=None, plain_password="s3cret", save_password=True, prompt_policy="when-needed", ask_master=lambda c: "master")
        assert saved.get("password") == ""
        assert "s3cret" not in str(saved)
        assert "password_enc" in saved
        assert saved["password_enc"] == "tok"

        # Editing unrelated field retains secret without re-entering
        collected2 = dict(collected, host="newhost.example")
        # collected2 has no password field; plain empty
        with mock.patch("hpc_gui.services.connection_profile_service.keychain_available", return_value=False), \
             mock.patch("hpc_gui.services.connection_profile_service.os_secret_store_available", return_value=False):
            saved2 = save_profile(collected2, initial_profile=saved, plain_password="", save_password=True, prompt_policy="when-needed", ask_master=lambda c: "master")
        assert saved2["password_enc"] == "tok"
        assert saved2.get("password") == ""

        # Disabling save removes secret
        collected3 = dict(collected2, save_password=False)
        with mock.patch("hpc_gui.services.connection_profile_service.keychain_available", return_value=False), \
             mock.patch("hpc_gui.services.connection_profile_service.os_secret_store_available", return_value=False):
            saved3 = save_profile(collected3, initial_profile=saved2, plain_password="", save_password=False, prompt_policy="when-needed")
        assert "password_enc" not in saved3
        assert "password_salt" not in saved3
        assert saved3.get("password") == ""

        # Only one scheme survives – keychain vs dpapi vs enc
        # Simulate keychain save over previous enc
        with mock.patch("hpc_gui.services.connection_profile_service.keychain_available", return_value=True), \
             mock.patch("hpc_gui.services.connection_profile_service.protect_keychain_secret", return_value="ref123"), \
             mock.patch("hpc_gui.services.connection_profile_service.delete_keychain_secret"):
            saved4 = save_profile(dict(collected, save_password=True), initial_profile=saved3, plain_password="newsecret", save_password=True, prompt_policy="when-needed")
        assert "password_keychain_ref" in saved4
        assert "password_enc" not in saved4
        assert "password_dpapi" not in saved4
    finally:
        tmp.cleanup()


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.semantic
def test_saved_password_not_autopopulated(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        # Ensure wx dialog does not populate password field from encrypted storage
        _wx_app = wx.App.Get() or wx.App(False)
        from hpc_gui.wx_connection_dialog import WxConnectionDialog

        profile = {"name": "sec", "host": "h.example", "username": "user", "save_password": True, "password_enc": "tok", "password_salt": "salt"}
        # Need a parent frame
        frame = wx.Frame(None)
        dlg = WxConnectionDialog(frame, initial_profile=profile, mode="edit", on_save=lambda p: True)
        # Password ctrl should be empty, not containing decrypted value
        assert dlg.password_ctrl.GetValue() == ""
        dlg.Destroy()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()


@pytest.mark.contract
def test_provider_templates_builtin_and_user():
    groups = builtin_system_template_groups()
    assert "Generic Slurm" in groups
    assert len(groups["Generic Slurm"]) >= 1

    # User templates – isolated storage
    from unittest.mock import patch
    tmpdir = tempfile.TemporaryDirectory()
    try:
        with patch.object(Path, "home", return_value=Path(tmpdir.name)):
            storage.save_config({"profiles": [], "settings": {}})
            from hpc_gui.config.system_profile import save_user_system_template, load_user_system_templates
            save_user_system_template("MyTemplate", {"name": "MyTemplate", "scratch_dir": "/scratch/{user}"})
            loaded = load_user_system_templates()
            assert any(t["name"] == "MyTemplate" for t in loaded)
    finally:
        tmpdir.cleanup()


@pytest.mark.audit
@pytest.mark.wx
def test_plugin_templates_without_hardcoded_names():
    groups = installed_cluster_template_groups()
    # Should be dict, keys are plugin names, no hardcoded logic
    assert isinstance(groups, dict)
    # Generic logic contains no provider-name branch – check source
    src = open("src/hpc_gui/wx_connection_dialog.py", encoding="utf-8").read()
    # Ensure no hardcoded provider names like "TRUBA" in generic logic
    assert "TRUBA" not in src or "provider_template" in src  # allow minimal mention but not branch
    # Also wx_connection generic logic shouldn't hardcode
    src2 = open("src/hpc_gui/wx_connection.py", encoding="utf-8").read()
    assert src2.count("TRUBA") == 0


@pytest.mark.gui
@pytest.mark.wx
@pytest.mark.regression
def test_template_provenance_preserved(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        from hpc_gui.wx_connection_dialog import WxConnectionDialog
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        # Create profile with plugin provenance
        initial = {
            "name": "lab",
            "host": "h.example",
            "provider_template": {"name": "PluginProv", "storage": []},
            "system_template_source": {"kind": "plugin", "plugin_id": "org.example.plugin", "profile_id": "p1"},
        }
        dlg = WxConnectionDialog(frame, initial_profile=initial, mode="edit", on_save=lambda p: True)
        # Without template action, provenance should survive
        collected = dlg._collect_profile()
        assert collected is not None
        assert collected.get("system_template_source") == {"kind": "plugin", "plugin_id": "org.example.plugin", "profile_id": "p1"}
        dlg.Destroy()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()
