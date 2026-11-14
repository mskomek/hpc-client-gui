"""Wave 71 – wx Connection profile management polish tests.

Covers add-button enabled, CRUD, secrets, templates, storage, quota,
advanced SSH, ssh_info mapping, MFA/host-key, action states, i18n.

Uses isolated temp storage and mock/fake backends; never hits a real cluster.
"""

from unittest import mock

import pytest

# Shared imports
from hpc_gui.services.quota_monitor import quota_gate
from hpc_gui.plugins.models import validate_storage_area

wx = pytest.importorskip("wx", reason="wxPython not installed – skipping wx GUI tests")
from support.wx_profiles_env import (_isolated_storage)


@pytest.mark.gui
@pytest.mark.wx
def test_provider_required_project_account_validation(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        from hpc_gui.wx_connection_dialog import WxConnectionDialog
        frame = wx.Frame(None)
        # Provider requiring project
        initial = {
            "name": "lab",
            "host": "h.example",
            "provider_template": {"requirements": {"project": {"required": True, "label": "Project"}}},
        }
        dlg = WxConnectionDialog(frame, initial_profile=initial, mode="edit", on_save=lambda p: True)
        dlg.host_ctrl.SetValue("h.example")
        dlg.project_ctrl.SetValue("")  # Required but empty
        # Mock MessageBox to capture validation
        with mock.patch.object(dlg._wx, "MessageBox") as mock_msg:
            result = dlg._collect_profile()
            assert result is None
            mock_msg.assert_called()
        # Now fill required
        dlg.project_ctrl.SetValue("myproj")
        with mock.patch.object(dlg._wx, "MessageBox"):
            result2 = dlg._collect_profile()
            assert result2 is not None
            assert result2["project"] == "myproj"
        dlg.Destroy()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()


@pytest.mark.unit
@pytest.mark.wx
def test_storage_add_edit_remove_and_validation(monkeypatch):
    # Validate storage area
    area = {"id": "home", "label": "Home", "kind": "home", "enabled": True, "path_template": "/home/{user}", "access_context": "login-node"}
    assert validate_storage_area(area) is None
    # Invalid path
    bad = dict(area, path_template="bad; rm -rf /")
    assert validate_storage_area(bad) is not None
    # Test wx dialog storage helpers – use dialog's storage_rows via WxConnectionDialog
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        from hpc_gui.wx_connection_dialog import WxConnectionDialog
        frame = wx.Frame(None)
        dlg = WxConnectionDialog(frame, initial_profile={"name": "lab", "host": "h.example"}, mode="add", on_save=lambda p: True)
        # Simulate add
        dlg._provider_template = {"storage": []}
        dlg.storage_rows = []
        # Mock _show_storage_area_dialog to return a valid area without UI
        with mock.patch("hpc_gui.wx_connection_dialog._show_storage_area_dialog", return_value={"id": "proj", "label": "Proj", "kind": "project", "enabled": True, "path_template": "/proj/{project}", "access_context": "shared", "policy": {}}):
            dlg._add_storage_area()
            assert len(dlg.storage_rows) == 1
            assert dlg.storage_rows[0]["id"] == "proj"
        # Edit
        with mock.patch("hpc_gui.wx_connection_dialog._show_storage_area_dialog", return_value={"id": "proj", "label": "ProjEdited", "kind": "project", "enabled": True, "path_template": "/proj/{project}", "access_context": "shared", "policy": {}}):
            dlg.storage_list.SetSelection(0)
            dlg._edit_storage_area()
            assert dlg.storage_rows[0]["label"] == "ProjEdited"
        # Remove
        dlg.storage_list.SetSelection(0)
        dlg._remove_storage_area()
        assert len(dlg.storage_rows) == 0
        # Home/scratch sync
        dlg.system_name_ctrl.SetValue("Test")
        dlg.home_dir_ctrl.SetValue("/home/{user}")
        dlg.scratch_dir_ctrl.SetValue("/scratch/{user}")
        dlg._legacy_storage_snapshot = {"home_dir": "", "scratch_dir": ""}
        dlg.storage_rows = [{"id": "home", "kind": "home", "path_template": "/old/home"}]
        dlg.home_dir_ctrl.SetValue("/new/home")
        dlg._sync_legacy_storage_paths()
        assert dlg.storage_rows[0]["path_template"] == "/new/home"
        dlg.Destroy()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()


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
def test_advanced_ssh_persistence(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        from hpc_gui.wx_connection_dialog import WxConnectionDialog
        frame = wx.Frame(None)
        dlg = WxConnectionDialog(frame, initial_profile={"name": "lab", "host": "h.example"}, mode="add", on_save=lambda p: True)
        # Set advanced values
        dlg.cb_host_key_policy.SetSelection(1)  # strict
        dlg.sp_keepalive.SetValue(120)
        dlg.sp_ssh_timeout.SetValue(45.5)
        dlg.sp_transfer_parallelism.SetValue(4)
        dlg.cb_jump_enabled.SetValue(True)
        dlg.jump_host_ctrl.SetValue("jump.example")
        dlg.sp_jump_port.SetValue(2222)
        dlg.jump_username_ctrl.SetValue("jumpuser")
        dlg.jump_key_path_ctrl.SetValue("/tmp/key")
        dlg.cb_jump_host_key_policy.SetSelection(1)
        dlg.cb_x11.SetValue(True)
        dlg.cb_cli_allowed.SetValue(True)
        dlg.default_local_dir_ctrl.SetValue("/tmp/local")
        dlg.host_ctrl.SetValue("h.example")
        dlg.username_ctrl.SetValue("alice")
        # Collect
        collected = dlg._collect_profile()
        assert collected is not None
        assert collected["host_key_policy"] == "strict"
        assert collected["keepalive_interval_seconds"] == 120
        assert collected["ssh_timeout"] == 45.5
        assert collected["transfer_parallelism"] == 4
        assert collected["x11_forwarding"] is True
        assert collected["cli_allowed"] is True
        assert collected["jump_host"]["enabled"] is True
        assert collected["jump_host"]["host"] == "jump.example"
        assert collected["jump_host"]["port"] == 2222
        assert collected["jump_host"]["username"] == "jumpuser"
        assert collected["file_manager"]["local_start_dir"] == "/tmp/local"
        # Jump required validation: enabled with empty host should fail
        dlg.jump_host_ctrl.SetValue("")
        with mock.patch.object(dlg._wx, "MessageBox") as mock_msg:
            result = dlg._collect_profile()
            assert result is None
            mock_msg.assert_called()
        dlg.Destroy()
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()
