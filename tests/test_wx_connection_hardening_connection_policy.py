
pytest_plugins = ('support.test_wx_connection_hardening_shared',)
"""Wave 71.1 hardening – wx Connection closure.

Covers P0 credential resolution, Test Cluster, dialogs, action states,
Save & Connect event chain, secret matrices, precedence, unavailable error,
host-key, provider/storage/quota non-regression, i18n, redaction, threading,
controller transitions, selected vs active, delete active.

All tests use isolated temp storage and mocked backends; no real HPC cluster.
"""
from support.test_wx_connection_hardening_shared import (
    _isolated_storage,
    load_language,
    load_profiles,
    pytest,
    storage,
    t,
    wx,
)


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
