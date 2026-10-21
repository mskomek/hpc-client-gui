from __future__ import annotations

import socket

from hpc_gui.ssh.command_runner import run_ssh_command


class _Channel:
    def __init__(self, exit_code: int = 0) -> None:
        self.exit_code = exit_code
        self.timeout = None

    def settimeout(self, timeout: float) -> None:
        self.timeout = timeout

    def recv_exit_status(self) -> int:
        return self.exit_code


class _Stream:
    def __init__(self, data: bytes = b"", *, timeout: bool = False) -> None:
        self.data = data
        self.timeout = timeout
        self.channel = _Channel()

    def read(self) -> bytes:
        if self.timeout:
            raise socket.timeout()
        return self.data


class _Client:
    def __init__(self, stdout: _Stream, stderr: _Stream) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.command = ""

    def exec_command(self, command: str):
        self.command = command
        return object(), self.stdout, self.stderr


def test_sensitive_command_and_terminal_controls_are_redacted_from_logs() -> None:
    client = _Client(
        _Stream(b"\x1b[31mready\x1b[0m\r\n"),
        _Stream(b"warning\r\n"),
    )
    messages: list[str] = []

    result = run_ssh_command(
        client,
        "sshpass -p topsecret ssh cluster",
        log=messages.append,
        connection_timeout=12,
    )

    assert client.command == "sshpass -p topsecret ssh cluster"
    assert result == (0, "\x1b[31mready\x1b[0m\r\n", "warning\r\n")
    assert "topsecret" not in "\n".join(messages)
    assert "SSH$ <redacted>" in messages
    assert "ready" in messages
    assert "\x1b" not in "\n".join(messages)
    assert client.stdout.channel.timeout == 12


def test_command_timeout_returns_shell_timeout_status() -> None:
    client = _Client(_Stream(timeout=True), _Stream())
    messages: list[str] = []

    result = run_ssh_command(
        client,
        "sleep 60",
        log=messages.append,
        timeout_s=0.25,
    )

    assert result == (124, "", "")
    assert "[timeout after" in messages[-1]
