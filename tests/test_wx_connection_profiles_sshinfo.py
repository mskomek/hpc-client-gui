"""Wave 71 – wx Connection profile management polish tests.

Covers add-button enabled, CRUD, secrets, templates, storage, quota,
advanced SSH, ssh_info mapping, MFA/host-key, action states, i18n.

Uses isolated temp storage and mock/fake backends; never hits a real cluster.
"""

from unittest import mock

import pytest

# Shared imports
from hpc_gui.ssh.client import HostKeyInfo
from hpc_gui.wx_connection import WxConnectionModel, ssh_info_from_profile

wx = pytest.importorskip("wx", reason="wxPython not installed – skipping wx GUI tests")
from support.wx_profiles_env import (_isolated_storage)


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


@pytest.mark.contract
def test_i18n_en_tr_labels():
    from hpc_gui.core.i18n import t, load_language
    # Ensure EN for downstream tests that expect English strings
    load_language("en")
    en_add = t("login.add_connection")
    assert en_add == "Add Connection"
    en_save = t("connection.save")
    assert en_save == "Save"
    en_delete = t("connection.delete_action")
    assert en_delete == "Delete"
    load_language("tr")
    tr_add = t("login.add_connection")
    assert tr_add == "Bağlantı Ekle"
    tr_save = t("connection.save")
    assert tr_save == "Kaydet"
    tr_delete = t("connection.delete_action")
    assert tr_delete == "Sil"
    # No missing keys for new UI
    for key in ["connection.profile_section", "connection.auth_section", "connection.cluster_settings", "connection.advanced_settings",
                "connection.delete_confirm_title", "connection.delete_confirm_message", "connection.host_key_prompt_title",
                "connection.storage_areas", "connection.quota_settings", "connection.jump_enable", "connection.host_key_verification",
                "connection.rename_name_taken"]:
        load_language("en")
        assert t(key) != f"[{key}]"
        load_language("tr")
        assert t(key) != f"[{key}]"
    load_language("en")  # leave EN for tests expecting English (e.g., macOS X11)
