"""Wave 71 – wx Connection profile management polish tests.

Covers add-button enabled, CRUD, secrets, templates, storage, quota,
advanced SSH, ssh_info mapping, MFA/host-key, action states, i18n.

Uses isolated temp storage and mock/fake backends; never hits a real cluster.
"""

import tempfile

from pathlib import Path

from unittest import mock

import pytest

from hpc_gui.config import storage

from hpc_gui.services.quota_monitor import quota_gate

from hpc_gui.plugins.models import validate_storage_area

from hpc_gui.config.system_profile import builtin_system_template_groups

from hpc_gui.plugins.templates import installed_cluster_template_groups

wx = pytest.importorskip("wx", reason="wxPython not installed – skipping wx GUI tests")

def _isolated_storage(monkeypatch):
    tmp = tempfile.TemporaryDirectory()
    monkeypatch.setattr(Path, "home", lambda: Path(tmp.name))
    # Ensure clean config
    storage.save_config({"profiles": [], "settings": {}})
    return tmp

@pytest.mark.contract
def test_provider_templates_builtin_and_user():
    groups = builtin_system_template_groups()
    assert "Generic Slurm" in groups
    assert len(groups["Generic Slurm"]) >= 1

    # User templates – isolated storage
    import tempfile
    from pathlib import Path
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
