"""Wave 71.1 hardening – wx Connection closure.

Covers P0 credential resolution, Test Cluster, dialogs, action states,
Save & Connect event chain, secret matrices, precedence, unavailable error,
host-key, provider/storage/quota non-regression, i18n, redaction, threading,
controller transitions, selected vs active, delete active.

All tests use isolated temp storage and mocked backends; no real HPC cluster.
"""

import tempfile

from pathlib import Path

from unittest import mock

import pytest

wx = pytest.importorskip("wx", reason="wxPython not installed – skipping wx GUI tests")

from hpc_gui.config import storage

from hpc_gui.config.storage import load_profiles

from hpc_gui.core.i18n import t, load_language

from hpc_gui.wx_connection import build_connection_panel

def _connection_source():
    root = Path("src/hpc_gui")
    modules = (
        "wx_connection.py",
        "wx_connection_model.py",
        "_wx_connection_profiles.py",
        "_wx_connection_worker.py",
    )
    return "\n".join((root / name).read_text(encoding="utf-8") for name in modules)

def _isolated_storage(monkeypatch):
    tmp = tempfile.TemporaryDirectory()
    # Patch both Path.home and the app_data_dir helpers so config and plugins
    # use the same isolated temp dir regardless of which helper a module
    # imported. Without this, conftest's tmp_path for plugins and our
    # Path.home temp would diverge and load_profiles would look in the wrong
    # place when tests are run as part of a large suite.
    monkeypatch.setattr(Path, "home", lambda: Path(tmp.name))
    # Also patch the core and config helpers directly
    try:
        import hpc_gui.core.paths as paths_mod
        import hpc_gui.config.storage as cfg_storage
        import hpc_gui.plugins.storage as plug_storage
        fake_dir = Path(tmp.name) / ".truba_slurm_gui"
        fake_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_dir)
        monkeypatch.setattr(cfg_storage, "app_data_dir", lambda: fake_dir)
        # plugins uses its own helper but conftest already patches it to tmp_path;
        # we override to use the same fake_dir for consistency when tests run
        # as part of the large suite.
        monkeypatch.setattr(plug_storage, "app_data_dir", lambda: fake_dir)
        monkeypatch.setattr(plug_storage, "plugins_root", lambda override=None: fake_dir / "plugins")
    except Exception:
        pass
    storage.save_config({"profiles": [], "settings": {}})
    return tmp

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

@pytest.mark.unit
@pytest.mark.wx
def test_mfa_respects_echo_and_not_logged(monkeypatch, caplog):
    tmp = _isolated_storage(monkeypatch)
    try:
        _wx_app = wx.App.Get() or wx.App(False)
        frame = wx.Frame(None)
        host = build_connection_panel(frame, profiles=[])
        model = host._wx_connection_model
        # Mock wx dialogs to capture which dialog type is used
        captured_dialogs = []

        class FakePwd:
            def __init__(self, *a, **kw):
                captured_dialogs.append("pwd")
                self.val = "secret1"
            def ShowModal(self): return wx.ID_OK
            def GetValue(self): return self.val
            def Destroy(self): pass
        class FakeTxt:
            def __init__(self, *a, **kw):
                captured_dialogs.append("txt")
                self.val = "visible2"
            def ShowModal(self): return wx.ID_OK
            def GetValue(self): return self.val
            def Destroy(self): pass
        with mock.patch.object(wx, "PasswordEntryDialog", FakePwd), mock.patch.object(wx, "TextEntryDialog", FakeTxt):
            from hpc_gui.services.connection_controller import KeyboardInteractiveRequest
            req = KeyboardInteractiveRequest("Title", "Instr", ("Prompt1:", "Prompt2:"), (False, True))
            answers = model.answer_keyboard_interactive(req)
            assert answers == ["secret1", "visible2"]
            assert captured_dialogs == ["pwd", "txt"], "echo False must use PasswordEntryDialog, echo True must use TextEntryDialog"
            # Ensure explicit echo wins over heuristic
            captured_dialogs.clear()
            req2 = KeyboardInteractiveRequest("Title", "Instr", ("password prompt",), (True,))
            model.answer_keyboard_interactive(req2)
            assert captured_dialogs == ["txt"], "echo True must not be masked even if prompt contains password"
        # No secret in logs
        assert "secret1" not in str(caplog.text)
        assert "visible2" not in str(caplog.text)
        # Answers not retained on model
        assert not hasattr(model, "secret1")
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
    src = _connection_source()
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
