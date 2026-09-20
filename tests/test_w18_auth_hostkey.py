"""W18 — authentication truthfulness + host-key security regression proofs.

Real code exercised: WxConnectionModel/ssh_info_from_profile decision plumbing,
wx panel connect-selected worker routing + controller states, translated failure
mapping shared with the Qt path (core.ui_errors.describe_connection_error).
Mocked boundary: SSH transport (connect callable raising real exception types /
mock-server wire errors); wx.MessageBox/MessageDialog chrome captured, never
the decision/handler logic under test.
Why legitimate: GUI tests prove panel event -> decision/message routing and
visible end-state; real wire authentication + host-key exchange are proven by
the mock-server probes, the EXTERNAL lab matrix and the existing SSH suites.
What these tests do NOT prove: real network authentication (see EXTERNAL).
"""

from __future__ import annotations

import time
from unittest import mock

import paramiko
import pytest

from hpc_gui.core.i18n import t
from hpc_gui.services.connection_controller import (
    HostKeyRequest,
    KeyboardInteractiveRequest,
)
from hpc_gui.ssh.client import (
    HostKeyChangedError,
    HostKeyInfo,
    HostKeyRejectedError,
    NoAuthenticationCredentialError,
)
from hpc_gui.wx_connection import (
    WxConnectionModel,
    describe_wx_connect_failure,
    format_host_key_prompt,
    ssh_info_from_profile,
)


@pytest.fixture(autouse=True)
def _english_ui():
    """Pin English strings: assertions check translated guidance, not key IDs."""
    from hpc_gui.core import i18n as _i18n

    previous = _i18n.current_language()
    _i18n.load_language("en")
    try:
        yield
    finally:
        try:
            _i18n.load_language(previous)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# DEF-W18-001: wx failure mapping (REQ HPC-W05-AUTH-005/006/007/013/014)
# ---------------------------------------------------------------------------

def test_wrong_password_maps_to_actionable_auth_message():
    """NEG-W18-AUTH-VISIBLE: wrong credential gets guidance, not raw text."""
    message = describe_wx_connect_failure(paramiko.AuthenticationException("Authentication failed."))
    assert t("connection.error_authentication") in message
    assert "mockuser" not in message


def test_missing_key_maps_to_key_file_guidance():
    """NEG-W18-KEY-ACTIONABLE: missing key path names the remedy + detail."""
    message = describe_wx_connect_failure(FileNotFoundError("No such file: '/tmp/missing_ed25519'"))
    assert t("connection.error_key_file") in message
    assert "missing_ed25519" in message


def test_host_key_changed_uses_translated_security_message():
    """NEG-W18-HOSTKEY-CHANGED: mismatch failure identifies host + remedy."""
    message = describe_wx_connect_failure(HostKeyChangedError("lab-host"))
    assert t("connection.host_key_changed").split("{host}")[0] in message
    assert "lab-host" in message


def test_host_key_rejected_uses_translated_security_message():
    """NEG-W18-HOSTKEY-REJECT: rejection identifies the host truthfully."""
    message = describe_wx_connect_failure(HostKeyRejectedError("lab-host"))
    assert t("connection.host_key_rejected").split("{host}")[0] in message
    assert "lab-host" in message


def test_no_credential_not_reported_as_wrong_password():
    """NEG-W18-NO-CREDENTIAL: missing credential is never 'wrong password'."""
    message = describe_wx_connect_failure(NoAuthenticationCredentialError())
    assert t("connection.error_no_credential") in message
    assert "wrong" not in message.lower()


def test_saved_secret_states_keep_their_messages():
    """CON-W18-SAVED-SECRET: stored-secret failures keep dedicated messages."""
    assert t("connection.saved_password_unavailable") in describe_wx_connect_failure(
        RuntimeError("saved_password_unavailable")
    )
    assert t("login.err_master_wrong") in describe_wx_connect_failure(
        RuntimeError("master_wrong")
    )
    assert t("connection.auth_cancelled") in describe_wx_connect_failure(
        RuntimeError("master_cancelled")
    )


def test_secret_never_echoed_in_failure_message():
    """REQ-W18-NO-LEAK: secret accidentally inside an error is redacted."""
    secret = "s3cr3t-pw-probe-value"
    message = describe_wx_connect_failure(
        RuntimeError(f"boom for {secret} happened"), resolved_password=secret
    )
    assert secret not in message
    assert "<redacted>" in message


# ---------------------------------------------------------------------------
# DEF-W18-002: host-key type must reach the prompt (REQ HPC-W05-AUTH-016)
# ---------------------------------------------------------------------------

def test_host_key_request_carries_key_type():
    """CON-W18-KEY-TYPE: transport key type survives into the GUI request."""
    seen = {}

    model = WxConnectionModel([], host_key_decision=lambda req: seen.setdefault("req", req) or "reject")
    profile = {"host": "h.example", "port": 22, "username": "u"}
    info = ssh_info_from_profile(profile, model)
    info.host_key_decision(HostKeyInfo("h.example", "ssh-ed25519", "aa:bb"))
    assert seen["req"].key_type == "ssh-ed25519"


def test_host_key_prompt_identifies_type_host_and_fingerprint():
    """REQ-W18-PROMPT-IDENTITY: prompt names type/host/fingerprint, no secret."""
    request = HostKeyRequest("h.example", "aa:bb:cc", "target", "ssh-ed25519")
    message = format_host_key_prompt(request)
    assert "ssh-ed25519" in message
    assert "h.example" in message
    assert "aa:bb:cc" in message


def test_keyboard_handler_gating_matches_provider_contract():
    """CON-W18-PROVIDER-AUTH: kbd-interactive offered only when applicable."""
    model = WxConnectionModel([])
    base = {"host": "h", "port": 22, "username": "u"}
    no_provider = ssh_info_from_profile(dict(base), model)
    assert no_provider.keyboard_interactive_handler is not None
    declared = ssh_info_from_profile(
        dict(base, provider_template={"access": {"auth_methods": ["password", "publickey"]}}), model
    )
    assert declared.keyboard_interactive_handler is None
    mfa = ssh_info_from_profile(
        dict(base, provider_template={"access": {"auth_methods": ["keyboard-interactive"]}}), model
    )
    assert mfa.keyboard_interactive_handler is not None


# ---------------------------------------------------------------------------
# GUI/event proofs (real wx app, panel, controller; dialog chrome captured)
# ---------------------------------------------------------------------------

def _isolated_profiles(monkeypatch, tmp_path):
    from hpc_gui.config import storage

    monkeypatch.setenv("HPC_GUI_CONFIG_ROOT", str(tmp_path / "cfg"))
    monkeypatch.setenv("HPC_GUI_STATE_ROOT", str(tmp_path / "state"))
    storage.save_config({"profiles": [], "settings": {}})
    return storage


def _pump_until(predicate, timeout_s=20):
    import wx

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        wx.YieldIfNeeded()
        if predicate():
            return True
        time.sleep(0.1)
    return predicate()


def _status_texts(host):
    import wx

    texts = []
    stack = [host]
    while stack:
        node = stack.pop()
        if isinstance(node, wx.StaticText):
            texts.append(node.GetLabel())
        stack.extend(node.GetChildren())
    return texts


def _build_panel_with_profile(frame, storage, name, connect):
    from hpc_gui.wx_connection import build_connection_panel

    storage.upsert_profile({"name": name, "host": "127.0.0.1", "port": 2222, "username": "u"})
    host = build_connection_panel(frame, profiles=storage.load_profiles(), connect=connect)
    model = host._wx_connection_model
    assert model.select(name) is True
    choices = host._wx_connection_controls["choices"]
    choices.SetStringSelection(name)
    import wx

    choices.GetEventHandler().ProcessEvent(
        wx.CommandEvent(wx.EVT_LISTBOX.typeId, choices.GetId())
    )
    return host, model


def _click_connect(host):
    import wx

    buttons = []

    def collect(root):
        for child in root.GetChildren():
            if isinstance(child, wx.Button) and child.GetName() == "ConnectSelected":
                buttons.append(child)
            collect(child)

    collect(host)
    assert buttons, "ConnectSelected button must exist"
    evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, buttons[0].GetId())
    buttons[0].GetEventHandler().ProcessEvent(evt)


@pytest.mark.wx
@pytest.mark.semantic
def test_gui_unknown_host_prompt_accept_reject_cancel(monkeypatch, tmp_path):
    """REQ-W18-HOSTKEY-DIALOG: real decision closure maps YES/NO/CANCEL + names key type.

    Real code exercised: model._host_key_decision closure (message format +
    decision mapping). Mocked boundary: wx.MessageDialog chrome (captured text
    + scripted result). Why legitimate: proves the adapter logic that turns a
    user gesture into a trust decision; native dialog rendering is platform
    chrome, not product logic.
    """
    import wx

    from hpc_gui.wx_connection import build_connection_panel

    storage = _isolated_profiles(monkeypatch, tmp_path)
    storage.upsert_profile({"name": "p", "host": "h", "port": 22, "username": "u"})
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None, title="w18-hostkey")
    try:
        host = build_connection_panel(frame, profiles=storage.load_profiles(), connect=lambda p: {"connected": True})
        decide = host._wx_connection_model._host_key_decision
        captured = {}

        def fake_dialog(parent, message, title, style):
            captured["message"] = message
            captured["title"] = title
            dlg = mock.Mock()
            dlg.ShowModal.return_value = fake_dialog.result
            return dlg

        request = HostKeyRequest("h.example", "aa:bb:cc", "target", "ssh-ed25519")
        with mock.patch.object(wx, "MessageDialog", side_effect=fake_dialog):
            fake_dialog.result = wx.ID_YES
            assert decide(request) == "save"
            assert "ssh-ed25519" in captured["message"]
            assert "h.example" in captured["message"]
            assert "aa:bb:cc" in captured["message"]
            fake_dialog.result = wx.ID_NO
            assert decide(request) == "once"
            fake_dialog.result = wx.ID_CANCEL
            assert decide(request) == "reject"
    finally:
        frame.Destroy()


@pytest.mark.wx
@pytest.mark.semantic
def test_gui_wrong_password_fails_visibly_with_actionable_message(monkeypatch, tmp_path):
    """REQ-W18-AUTH-005: wrong-password connect ends FAILED with guidance.

    Real code exercised: ConnectSelected event, worker routing, controller
    fail transition, visible status label. Mocked boundary: transport (raises
    AuthenticationException like a real server rejection); MessageBox chrome
    captured.
    """
    import wx

    storage = _isolated_profiles(monkeypatch, tmp_path)
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None, title="w18-wrongpw")
    shown = {}
    real_box = wx.MessageBox
    try:
        def boom(profile):
            raise paramiko.AuthenticationException("Authentication failed.")

        host, model = _build_panel_with_profile(frame, storage, "badpw", boom)
        with mock.patch.object(wx, "MessageBox", side_effect=lambda *a, **k: shown.setdefault("text", a[0]) or wx.ID_OK):
            _click_connect(host)
            ok = _pump_until(
                lambda: any("ail" in label for label in _status_texts(host))
                and model.controller.state.value == "failed"
            )
        assert ok, "wrong password must reach a visibly failed state"
        assert t("connection.error_authentication") in shown.get("text", "")
    finally:
        frame.Destroy()


@pytest.mark.wx
@pytest.mark.semantic
def test_gui_missing_key_actionable_and_changed_key_hard_fail(monkeypatch, tmp_path):
    """REQ-W18-AUTH-007/013: missing key guides; changed key hard-fails mapped."""
    import wx

    storage = _isolated_profiles(monkeypatch, tmp_path)
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None, title="w18-keyerrs")
    try:
        def missing(profile):
            raise FileNotFoundError("No such file: '/tmp/missing_ed25519'")

        host, model = _build_panel_with_profile(frame, storage, "nokey", missing)
        shown = {}
        with mock.patch.object(wx, "MessageBox", side_effect=lambda *a, **k: shown.setdefault("text", a[0]) or wx.ID_OK):
            _click_connect(host)
            ok = _pump_until(lambda: model.controller.state.value == "failed")
        assert ok
        assert t("connection.error_key_file") in shown.get("text", ""), shown

        def changed(profile):
            raise HostKeyChangedError("lab-host")

        host2, model2 = _build_panel_with_profile(frame, storage, "chkey", changed)
        shown2 = {}
        with mock.patch.object(wx, "MessageBox", side_effect=lambda *a, **k: shown2.setdefault("text", a[0]) or wx.ID_OK):
            _click_connect(host2)
            ok2 = _pump_until(lambda: model2.controller.state.value == "failed")
        assert ok2
        assert "lab-host" in shown2.get("text", ""), shown2
        assert t("connection.host_key_changed").split("{host}")[0] in shown2.get("text", "")
    finally:
        frame.Destroy()


@pytest.mark.wx
@pytest.mark.semantic
def test_gui_master_cancel_returns_to_safe_state(monkeypatch, tmp_path):
    """REQ-W18-AUTH-008: cancelled auth leaves safe state, no error popup."""
    import wx

    storage = _isolated_profiles(monkeypatch, tmp_path)
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None, title="w18-cancel")
    try:
        def cancelled(profile):
            raise RuntimeError("master_cancelled")

        host, model = _build_panel_with_profile(frame, storage, "cancelme", cancelled)
        calls = []
        with mock.patch.object(wx, "MessageBox", side_effect=lambda *a, **k: calls.append(a[0]) or wx.ID_OK):
            _click_connect(host)
            ok = _pump_until(lambda: model.controller.state.value in ("failed", "disconnected"))
        assert ok
        assert calls == [], "cancel must not pop an error dialog"
        assert any("ancell" in label for label in _status_texts(host))
    finally:
        frame.Destroy()
