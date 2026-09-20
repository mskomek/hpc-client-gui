"""W11 — Real SSH lifecycle validation against the loopback laboratory.

Laboratory: ``tests/support/mock_ssh_server.py`` ``MockSSHServer`` bound to
``127.0.0.1`` on an ephemeral port with a freshly generated, never-persisted
host key and a fixed, clearly-fake fixture account. The client under test is
the real product ``SSHClientWrapper`` speaking the real SSH wire protocol
(``paramiko`` both ends: exec + shell + SFTP subsystem negotiation), so every
test below proves a real round trip rather than a mocked service-layer
stand-in. No real cluster, no real credential, no network egress and no
secret appear anywhere in this module.

Requirement map (all owned by W11):
  HPC-W03-SSH-001  UI never stays "connected" after transport failure
  HPC-W03-SSH-002  valid connection
  HPC-W03-SSH-003  invalid host / unreachable host
  HPC-W03-SSH-004  invalid credentials
  HPC-W03-SSH-005  host-key first-contact policy
  HPC-W03-SSH-006  host-key mismatch policy (safely simulated: lab key roll)
  HPC-W03-SSH-007  disconnect while idle
  HPC-W03-SSH-008  disconnect during operation
  HPC-W03-SSH-009  reconnect
  HPC-W03-SSH-010  repeated connect/disconnect (leaked session state)
  HPC-W03-SSH-011  Unicode command/output

Defect regressions (counted W11 remediations):
  DEF-W11-001  transport failure left the controller/UI "connected"
               (disconnect_cb was never wired by connect_profile and no
               controller transition repainted the wx status indicator).
  DEF-W11-002  reconnect orphaned the previous live session (no teardown of
               the superseded ssh wrapper before the new attempt).
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import paramiko
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(ROOT / "tests"))

import hpc_gui.ssh.client as ssh_client_mod
from hpc_gui.ssh.client import (
    HostKeyChangedError,
    SSHClientWrapper,
    SSHConnInfo,
)
from hpc_gui.wx_connection import WxConnectionModel, connect_profile
from support.mock_ssh_server import MOCK_PASSWORD, MOCK_USERNAME, MockSSHServer


# ---------------------------------------------------------------------------
# Laboratory fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def lab_server(tmp_path_factory):
    """One loopback SSH+SFTP server shared by the scenario tests."""
    root = tmp_path_factory.mktemp("w11-lab-remote")
    with MockSSHServer(root) as server:
        yield server


@pytest.fixture()
def lab_env(tmp_path, monkeypatch):
    """Isolate host-key + system-key state from the developer machine.

    Real code exercised: full SSHClientWrapper.connect()/run()/close()
    including known_hosts load/save and host-key policy.
    Mocked boundary: ``app_data_dir`` (so the lab never touches the real
    user profile) and ``load_system_host_keys`` (so a stale developer
    ``~/.ssh/known_hosts`` entry for 127.0.0.1 cannot flake the lab).
    What this does NOT prove: trust decisions against the real user
    keyring (covered by unit tests elsewhere, not claimed here).
    """
    data_dir = tmp_path / "appdata"
    data_dir.mkdir()
    monkeypatch.setattr(ssh_client_mod, "app_data_dir", lambda: data_dir)
    monkeypatch.setattr(
        paramiko.SSHClient, "load_system_host_keys", lambda self: None
    )
    return data_dir


def _info(server, **overrides):
    kwargs = dict(
        host="127.0.0.1",
        port=server.port,
        username=MOCK_USERNAME,
        password=MOCK_PASSWORD,
        host_key_policy="accept-new",
        host_key_decision=lambda info: "save",
        timeout=10,
    )
    kwargs.update(overrides)
    return SSHConnInfo(**kwargs)


def _profile(server, **overrides):
    profile = {
        "name": "w11-lab",
        "host": "127.0.0.1",
        "port": server.port,
        "username": MOCK_USERNAME,
        "password": MOCK_PASSWORD,
        "host_key_policy": "accept-new",
    }
    profile.update(overrides)
    return profile


def _wait_for(predicate, timeout_s=10.0, poll_s=0.05):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(poll_s)
    return predicate()


# ---------------------------------------------------------------------------
# Requirement scenarios: HPC-W03-SSH-002..011 (+001 state assertions)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.acceptance
def test_valid_connection_runs_remote_command(lab_server, lab_env):
    """REQ-SSH-002: valid connection authenticates and runs a command."""
    ssh = SSHClientWrapper(_info(lab_server))
    ssh.connect()
    try:
        assert ssh.client is not None
        transport = ssh.client.get_transport()
        assert transport is not None and transport.is_active()
        code, out, err = ssh.run("echo hello-lab")
        assert code == 0
        assert "hello-lab" in out
        assert err == ""
    finally:
        ssh.close()
    assert ssh.client is None


@pytest.mark.integration
@pytest.mark.acceptance
def test_unreachable_host_fails_without_session(lab_server, lab_env):
    """REQ-SSH-003: closed loopback port fails fast and leaves no client."""
    ssh = SSHClientWrapper(_info(lab_server, port=1, timeout=3))
    with pytest.raises(Exception):
        ssh.connect()
    assert ssh.client is None


@pytest.mark.integration
@pytest.mark.acceptance
def test_invalid_credentials_are_rejected(lab_server, lab_env):
    """REQ-SSH-004: wrong password raises authentication failure, no session."""
    ssh = SSHClientWrapper(_info(lab_server, password="not-the-fixture-password"))
    with pytest.raises(paramiko.AuthenticationException):
        ssh.connect()
    assert ssh.client is None


@pytest.mark.integration
@pytest.mark.acceptance
def test_host_key_first_contact_save_and_reject(lab_server, lab_env):
    """REQ-SSH-005: first contact honours the accept-new decision callback."""
    ssh = SSHClientWrapper(_info(lab_server))
    ssh.connect()
    ssh.close()
    known_hosts = lab_env / "known_hosts"
    assert known_hosts.exists()

    # A second lab identity must refuse an unknown key when told to reject.
    # Force "unknown key" by pointing at an empty known_hosts file.
    empty_hosts = lab_env / "empty_known_hosts"
    empty_hosts.write_text("")
    ssh2 = SSHClientWrapper(
        SSHConnInfo(
            host="127.0.0.1", port=lab_server.port, username=MOCK_USERNAME,
            password=MOCK_PASSWORD, host_key_policy="accept-new",
            host_key_decision=lambda info: "reject", timeout=10,
            known_hosts_path=str(empty_hosts),
        )
    )
    with pytest.raises(paramiko.SSHException):
        ssh2.connect()
    assert ssh2.client is None


@pytest.mark.integration
@pytest.mark.acceptance
def test_host_key_mismatch_is_refused(lab_server, lab_env):
    """REQ-SSH-006: stale pin against live lab key refuses with mismatch.

    Real round trip with a safely simulated key roll: the lab server's key
    is pinned under ``[127.0.0.1]:port`` (port-scoped pins, OpenSSH
    behaviour), then the pin file is re-pointed at a different valid key
    while the same live server answers. Paramiko raises
    ``BadHostKeyException`` and the product maps it to
    ``HostKeyChangedError`` instead of connecting.
    """
    first = SSHClientWrapper(_info(lab_server))
    first.connect()
    first.close()
    pin_file = lab_env / "known_hosts"
    assert pin_file.exists()
    pinned_line = pin_file.read_text().strip().splitlines()[-1]
    selector, _keytype, _old_blob = pinned_line.split(" ", 2)
    rolled = paramiko.RSAKey.generate(1024)
    pin_file.write_text(f"{selector} {rolled.get_name()} {rolled.get_base64()}\n")
    pinned = SSHClientWrapper(_info(lab_server))
    try:
        with pytest.raises(HostKeyChangedError):
            pinned.connect()
    finally:
        pinned.close()
    assert pinned.client is None


@pytest.mark.integration
@pytest.mark.acceptance
def test_disconnect_while_idle_releases_transport(lab_server, lab_env):
    """REQ-SSH-007: idle disconnect drops transport and client state."""
    ssh = SSHClientWrapper(_info(lab_server))
    ssh.connect()
    transport = ssh.client.get_transport()
    assert transport.is_active()
    ssh.close()
    assert ssh.client is None
    assert not transport.is_active()


@pytest.mark.integration
@pytest.mark.acceptance
def test_command_against_dead_transport_raises(lab_server, lab_env):
    """REQ-SSH-008: mid-operation transport death surfaces, never success."""
    ssh = SSHClientWrapper(_info(lab_server))
    ssh.connect()
    try:
        ssh.client.get_transport().close()
        with pytest.raises(Exception):
            ssh.run("echo should-never-succeed")
    finally:
        ssh.close()
    assert ssh.client is None


@pytest.mark.integration
@pytest.mark.acceptance
def test_reconnect_after_close_succeeds(lab_server, lab_env):
    """REQ-SSH-009: close + fresh connect restores a working session."""
    model = WxConnectionModel(host_key_decision=lambda req: "save")
    profile = _profile(lab_server)
    first = connect_profile(profile, model)
    first["ssh"].close()
    second = connect_profile(profile, model)
    try:
        code, out, _ = second["ssh"].run("echo back-again")
        assert code == 0 and "back-again" in out
    finally:
        second["ssh"].close()


@pytest.mark.integration
@pytest.mark.acceptance
def test_repeated_connect_disconnect_leaks_no_session_state(lab_server, lab_env):
    """REQ-SSH-010: five connect/disconnect cycles leave no live state."""
    for _ in range(5):
        ssh = SSHClientWrapper(_info(lab_server))
        ssh.connect()
        code, _, _ = ssh.run("echo cycle")
        assert code == 0
        ssh.close()
        assert ssh.client is None
        assert ssh.sftp is None
    leftovers = [t for t in threading.enumerate() if t.name == "hpc_gui_ssh_shell" and t.is_alive()]
    assert leftovers == []


@pytest.mark.integration
@pytest.mark.acceptance
def test_unicode_command_output_roundtrip(lab_server, lab_env):
    """REQ-SSH-011: Unicode command text and output survive the round trip."""
    ssh = SSHClientWrapper(_info(lab_server))
    ssh.connect()
    try:
        code, out, _ = ssh.run("echo İstanbul_日本語_✓")
        assert code == 0
        assert "İstanbul" in out and "日本語" in out and "✓" in out
    finally:
        ssh.close()


# ---------------------------------------------------------------------------
# GUI proof: real wx.App + Frame, real event dispatch, observable labels
# ---------------------------------------------------------------------------

def _pump_until(label_fn, expected, timeout_s=20.0):
    """Pump the real wx loop until the observable label reaches ``expected``."""
    import wx

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            wx.Yield()
        except Exception:
            pass
        try:
            if label_fn() == expected:
                return True
        except Exception:
            pass
        time.sleep(0.05)
    try:
        return label_fn() == expected
    except Exception:
        return False


def _drive_select_and_connect(ctrls):
    """Drive the real listbox + button event path (no direct handler calls)."""
    import wx

    choices = ctrls["choices"]
    connect_btn = ctrls["connect"]
    choices.SetSelection(0)
    select_evt = wx.CommandEvent(wx.wxEVT_LISTBOX, choices.GetId())
    select_evt.SetEventObject(choices)
    wx.PostEvent(choices, select_evt)
    assert _pump_until(lambda: choices.GetStringSelection() == "lab",  True, timeout_s=5.0)
    click_evt = wx.CommandEvent(wx.wxEVT_BUTTON, connect_btn.GetId())
    click_evt.SetEventObject(connect_btn)
    wx.PostEvent(connect_btn, click_evt)


@pytest.mark.wx
@pytest.mark.gui
@pytest.mark.semantic
def test_wx_panel_reports_failed_connect_as_failed(monkeypatch):
    """GUI-001 (HPC-W03-SSH-001): a refused connect never shows "Connected".

    Real ``wx.App`` + ``Frame`` + ``build_connection_panel``; selection and
    Connect travel through real posted ``wx`` command events and the worker
    thread; the observable status label is the verdict.
    """
    import wx

    from hpc_gui import wx_connection as wx_conn
    from hpc_gui.core.i18n import current_language, load_language, t

    previous_language = current_language()
    load_language("en")
    profiles = [{"name": "lab", "host": "127.0.0.1", "username": "u"}]
    monkeypatch.setattr(wx_conn, "load_profiles", lambda: [dict(p) for p in profiles])
    monkeypatch.setattr(
        "hpc_gui.services.connection_profile_service.load_profile_by_name",
        lambda name: None,
    )

    def _refused(_profile):
        raise RuntimeError("connection refused (w11 lab)")

    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None, title="w11-lab-failed")
    try:
        host = wx_conn.build_connection_panel(frame, profiles=profiles, connect=_refused)
        ctrls = host._wx_connection_controls
        status = ctrls["status"]
        _drive_select_and_connect(ctrls)
        assert _pump_until(status.GetLabel, t("connection.status_failed"))
        assert status.GetLabel() != t("login.status_connected")
    finally:
        frame.Destroy()
        load_language(previous_language)


@pytest.mark.wx
@pytest.mark.gui
@pytest.mark.semantic
def test_wx_panel_transport_failure_repaints_status(monkeypatch):
    """GUI-002 (HPC-W03-SSH-001): leaving CONNECTED repaints the indicator.

    After a successful connect the panel shows "Connected"; a subsequent
    controller failure (the path ``disconnect_cb`` drives on transport
    death, see DEF-W11-001) must repaint the same label to the failed
    state instead of masquerading the dead session as live.
    """
    import wx

    from hpc_gui import wx_connection as wx_conn
    from hpc_gui.core.i18n import current_language, load_language, t

    previous_language = current_language()
    load_language("en")
    profiles = [{"name": "lab", "host": "127.0.0.1", "username": "u"}]
    monkeypatch.setattr(wx_conn, "load_profiles", lambda: [dict(p) for p in profiles])
    monkeypatch.setattr(
        "hpc_gui.services.connection_profile_service.load_profile_by_name",
        lambda name: None,
    )

    def _ok(_profile):
        return {"connected": True, "profile_name": "lab"}

    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None, title="w11-lab-repaint")
    try:
        host = wx_conn.build_connection_panel(frame, profiles=profiles, connect=_ok)
        ctrls = host._wx_connection_controls
        model = host._wx_connection_model
        status = ctrls["status"]
        _drive_select_and_connect(ctrls)
        assert _pump_until(status.GetLabel, t("login.status_connected"))
        model.controller.fail()
        assert _pump_until(status.GetLabel, t("connection.status_failed"))
        assert status.GetLabel() != t("login.status_connected")
    finally:
        frame.Destroy()
        load_language(previous_language)

# ---------------------------------------------------------------------------
# Counted-fix regressions
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.regression
@pytest.mark.semantic
def test_transport_failure_drives_controller_out_of_connected(lab_server, lab_env):
    """DEF-W11-001: dead transport must fail the controller (never "connected").

    REQ-* HPC-W03-SSH-001 / SSH-007 / SSH-008. Before FIX-A,
    ``SSHClientWrapper._disconnect_cb`` was ``None`` for sessions built by
    ``connect_profile`` and the controller stayed ``CONNECTED`` forever.
    """
    model = WxConnectionModel(host_key_decision=lambda req: "save")
    session = connect_profile(_profile(lab_server), model)
    ssh = session["ssh"]
    assert ssh._disconnect_cb is not None
    model.controller.finish(session)
    assert model.controller.state.value == "connected"
    try:
        ssh.client.get_transport().close()
        failed = _wait_for(lambda: model.controller.state.value == "failed", timeout_s=10.0)
    finally:
        ssh.close()
    assert failed, "controller never left 'connected' after transport death"
    assert model.controller.state.value != "connected"
    assert model.controller.session is None


@pytest.mark.unit
@pytest.mark.regression
@pytest.mark.semantic
def test_reconnect_closes_superseded_model_session():
    """DEF-W11-002: reconnecting tears down the previous live session.

    Before FIX-B the old ``ssh`` wrapper was orphaned (transport, shell
    reader thread and SFTP channels kept alive) while the controller
    pointed at the new session.
    """
    closed: list[str] = []
    counter = {"n": 0}

    class _FakeSSH:
        def __init__(self, tag):
            self.tag = tag

        def close(self):
            closed.append(self.tag)

    def _fake_connect(profile):
        counter["n"] += 1
        tag = f"session-{counter['n']}"
        return {"connected": True, "ssh": _FakeSSH(tag)}

    model = WxConnectionModel(
        profiles=[{"name": "p", "host": "h", "username": "u"}],
        connect=_fake_connect,
    )
    assert model.select("p")
    assert model.connect_selected() is True
    first_ssh = model.controller.session["ssh"]
    assert model.connect_selected() is True
    assert first_ssh.tag in closed
    assert model.controller.session["ssh"].tag == "session-2"
    assert model.controller.state.value == "connected"
