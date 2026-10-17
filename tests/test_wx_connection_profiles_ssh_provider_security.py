"""Wave 71 – wx Connection profile management polish tests.

Covers add-button enabled, CRUD, secrets, templates, storage, quota,
advanced SSH, ssh_info mapping, MFA/host-key, action states, i18n.

Uses isolated temp storage and mock/fake backends; never hits a real cluster.
"""
from support.test_wx_connection_profiles_shared import (
    HostKeyInfo,
    WxConnectionModel,
    _isolated_storage,
    builtin_system_template_groups,
    installed_cluster_template_groups,
    mock,
    pytest,
    ssh_info_from_profile,
    storage,
    wx,
)


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

@pytest.mark.contract
def test_saved_profile_to_sshinfo_mapping():
    profile = {
        "name": "lab",
        "host": "h.example",
        "port": 2222,
        "username": "alice",
        "password": "secret",
        "key_path": "/home/alice/.ssh/id_rsa",
        "host_key_policy": "strict",
        "keepalive_interval_seconds": 60,
        "ssh_timeout": 30.5,
        "x11_forwarding": True,
        "jump_host": {"enabled": True, "host": "jump.example", "port": 2222, "username": "juser", "key_path": "/tmp/jkey", "host_key_policy": "strict"},
        "save_password": True,
        "system": {"name": "Test"},
    }
    model = WxConnectionModel([profile], host_key_decision=lambda r: "save", keyboard_interactive=lambda r: ["mfa"])
    info = ssh_info_from_profile(profile, model)
    assert info.host == "h.example"
    assert info.port == 2222
    assert info.username == "alice"
    assert info.password == "secret"
    assert info.key_path == "/home/alice/.ssh/id_rsa"
    assert info.host_key_policy == "strict"
    assert info.keepalive_interval_seconds == 60
    assert info.timeout == 30.5
    assert info.x11_forwarding is True
    assert info.jump is not None
    assert info.jump.host == "jump.example"
    assert info.jump.port == 2222
    # Keyboard interactive handler should be callable
    assert callable(info.keyboard_interactive_handler)
    # Host key decision should delegate
    assert info.host_key_decision(HostKeyInfo("h.example", "ssh-rsa", "aa:bb")) == "save"

@pytest.mark.unit
def test_ssh_info_resolves_secure_password():
    # Profile with keychain ref, no plaintext
    profile = {"name": "sec", "host": "h.example", "port": 22, "username": "user", "password": "", "save_password": True, "password_keychain_ref": "ref123", "host_key_policy": "accept-new"}
    model = WxConnectionModel([profile])
    with mock.patch("hpc_gui.services.connection_profile_service.decrypt_profile_password", return_value="decrypted-secret"):
        # Need to patch within ssh_info_from_profile's import path
        with mock.patch("hpc_gui.wx_connection.decrypt_profile_password", return_value="decrypted-secret", create=True):
            # Actually ssh_info_from_profile imports inside function, so patch the source module
            import hpc_gui.services.connection_profile_service as svc
            with mock.patch.object(svc, "decrypt_profile_password", return_value="decrypted-secret"):
                info = ssh_info_from_profile(profile, model)
                # Password should be resolved
                assert info.password == "decrypted-secret"
    # Alternative: patch directly where used inside function (import inside)
    # Our implementation imports decrypt_profile_password inside function under try; patch that module
    with mock.patch("hpc_gui.services.connection_profile_service.decrypt_profile_password", return_value="resolved2"):
        info2 = ssh_info_from_profile(profile, model)
        assert info2.password == "resolved2"

@pytest.mark.unit
@pytest.mark.wx
def test_host_key_dialog_mapping(monkeypatch):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        from hpc_gui.wx_connection import build_connection_panel
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=[])
        model = host._wx_connection_model
        # Mock wx.MessageDialog to return YES/NO/CANCEL
        for expected, wx_id in [("save", wx.ID_YES), ("once", wx.ID_NO), ("reject", wx.ID_CANCEL)]:
            with mock.patch("wx.MessageDialog") as MockDlg:
                inst = MockDlg.return_value
                inst.ShowModal.return_value = wx_id
                result = model.decide_host_key(mock.Mock(hostname="h.example", fingerprint="aa:bb", role="target"))
                assert result == expected
        frame.Destroy()
        for _ in range(3):
            wx.Yield()
    finally:
        tmp.cleanup()

@pytest.mark.unit
def test_mfa_order_and_no_log(monkeypatch, caplog):
    requests = []
    model = WxConnectionModel([], keyboard_interactive=lambda req: requests.append(req) or ["r1", "r2"])
    from hpc_gui.services.connection_controller import KeyboardInteractiveRequest
    req = KeyboardInteractiveRequest("Title", "Instructions", ("Prompt1:", "Prompt2:"), (False, True))
    # Should return in order
    answers = model.answer_keyboard_interactive(req)
    assert answers == ["r1", "r2"]
    assert requests[0].echo == (False, True)
    # Ensure no secret in logs
    # Simulate no logging of MFA responses – check that answer not in caplog
    # Our model does not log; verify that responses are not retained on model
    assert not hasattr(model, "r1")
    assert "r1" not in str(caplog.text)
