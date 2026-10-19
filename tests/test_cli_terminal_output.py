from __future__ import annotations

from types import SimpleNamespace

from hpc_gui.cli import session as cli_session
from hpc_gui.cli.terminal_input import normalize_terminal_key


def test_terminal_session_activates_deferred_shell_output(monkeypatch):
    state = {"activated": False}

    class FakeSSH:
        def __init__(self, **_kwargs):
            pass

        def connect(self):
            state["connected"] = True

        def activate_shell_output(self):
            state["activated"] = True

        def close(self):
            pass

    class FakeFiles:
        def __init__(self, _ssh):
            pass

    monkeypatch.setattr(cli_session, "build_ssh_conn_info", lambda _args: object())
    monkeypatch.setattr(cli_session, "SSHClientWrapper", FakeSSH)
    monkeypatch.setattr(cli_session, "SSHFilesBackend", FakeFiles)
    args = SimpleNamespace(
        group="terminal",
        transport="sftp",
        verbose=False,
        profile="arf",
    )

    opened = cli_session.CLISession.open(args)
    opened.close()

    assert state == {"connected": True, "activated": True}


def test_terminal_input_maps_enter_to_carriage_return():
    assert normalize_terminal_key("\n") == "\r"
    assert normalize_terminal_key("\r") == "\r"


def test_terminal_input_maps_backspace_to_delete_key():
    assert normalize_terminal_key("\b") == "\x7f"
