"""Active Paramiko shell wiring for opt-in authenticated X11."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from hpc_gui.ssh import client as ssh_client
from hpc_gui.ssh import x11_shell
from hpc_gui.ssh.contracts import SSHConnInfo

pytestmark = pytest.mark.unit


class _Channel:
    def __init__(self, events):
        self.events = events

    def get_pty(self, **options):
        self.events.append(("pty", options))

    def invoke_shell(self):
        self.events.append(("shell",))

    def close(self):
        self.events.append(("channel-close",))


class _Forwarder:
    def __init__(self, events, *, fail_request=False):
        self.events = events
        self.fail_request = fail_request
        self.display = SimpleNamespace(connect=self._connect)

    def _connect(self, **_kwargs):
        self.events.append(("display-probe",))
        return SimpleNamespace(close=lambda: self.events.append(("display-close",)))

    def request(self, _channel):
        self.events.append(("request-x11",))
        if self.fail_request:
            raise RuntimeError("refused")

    def close(self):
        self.events.append(("forwarder-close",))


class _Transport:
    def __init__(self, channel, events):
        self.channel = channel
        self.events = events

    def is_active(self):
        return True

    def open_session(self, *, timeout):
        self.events.append(("open-session", timeout))
        return self.channel


class _SSH:
    def __init__(self, transport):
        self.transport = transport

    def get_transport(self):
        return self.transport


def test_request_x11_precedes_pty_and_shell(monkeypatch):
    events = []
    channel = _Channel(events)
    forwarder = _Forwarder(events)
    monkeypatch.setattr(x11_shell, "X11Forwarder", lambda **_kwargs: forwarder)

    opened, attached = x11_shell.open_x11_shell(
        _SSH(_Transport(channel, events)),
        log=lambda _message: None,
        timeout=4,
        term="xterm",
        width=90,
        height=30,
    )

    assert opened is channel
    assert attached is forwarder
    names = [event[0] for event in events]
    assert names.index("request-x11") < names.index("pty") < names.index("shell")
    assert ("pty", {"term": "xterm", "width": 90, "height": 30}) in events


def test_rejected_x11_request_closes_channel_and_fails_closed(monkeypatch):
    events = []
    channel = _Channel(events)
    forwarder = _Forwarder(events, fail_request=True)
    monkeypatch.setattr(x11_shell, "X11Forwarder", lambda **_kwargs: forwarder)

    with pytest.raises(x11_shell.X11Unavailable, match="cookie missing or SSH forwarding refused"):
        x11_shell.open_x11_shell(
            _SSH(_Transport(channel, events)), log=lambda _message: None, term="xterm"
        )

    assert ("channel-close",) in events
    assert ("forwarder-close",) in events
    assert ("pty", {"term": "xterm"}) not in events


def test_profile_off_keeps_existing_paramiko_shell_path(monkeypatch):
    wrapper = ssh_client.SSHClientWrapper(SSHConnInfo("host", 22))
    expected = object()
    wrapper.client = SimpleNamespace(invoke_shell=lambda **_kwargs: expected)

    assert wrapper._invoke_shell(term="xterm") is expected


def test_profile_on_uses_integrated_shell_and_closes_forwarder(monkeypatch):
    messages = []
    wrapper = ssh_client.SSHClientWrapper(
        SSHConnInfo("host", 22, x11_forwarding=True), logger=messages.append
    )
    channel = object()
    closed = []
    forwarder = SimpleNamespace(close=lambda: closed.append(True))
    wrapper.client = SimpleNamespace(
        invoke_shell=lambda **_kwargs: pytest.fail("must use the X11 shell opener")
    )
    monkeypatch.setattr(
        x11_shell, "open_x11_shell", lambda *args, **kwargs: (channel, forwarder)
    )

    assert wrapper._invoke_shell(term="xterm") is channel
    assert wrapper._x11_shell._forwarder is forwarder
    wrapper._stop_shell_session()
    assert closed == [True]
    assert wrapper._x11_shell._forwarder is None


def test_missing_local_cookie_does_not_fall_back_to_normal_ssh(monkeypatch):
    wrapper = ssh_client.SSHClientWrapper(
        SSHConnInfo("host", 22, x11_forwarding=True), logger=lambda _msg: None
    )
    expected = object()
    wrapper.client = SimpleNamespace(invoke_shell=lambda **_kwargs: expected)
    monkeypatch.setattr(
        x11_shell,
        "open_x11_shell",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            x11_shell.X11Unavailable("local cookie missing")
        ),
    )

    with pytest.raises(x11_shell.X11Unavailable, match="local cookie missing"):
        wrapper._invoke_shell(term="xterm")


def test_x11_failure_does_not_retry_shell_with_another_terminal_type():
    from hpc_gui.ssh.shell_session import InteractiveShellSession

    terms = []

    def invoke(**options):
        terms.append(options["term"])
        raise x11_shell.X11Unavailable("untrusted X11 unavailable")

    session = InteractiveShellSession(invoke_shell=invoke, geometry=(80, 24))
    assert session.start() is False
    assert terms == ["xterm-256color"]
