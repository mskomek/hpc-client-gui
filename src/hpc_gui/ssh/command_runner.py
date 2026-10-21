"""Execute and report one command over an authenticated SSH client."""

from __future__ import annotations

import socket
from typing import Callable, Optional

from hpc_gui.core.debug_support import timed
from hpc_gui.services.command_history_store import is_sensitive_command
from hpc_gui.ssh.shell_session import _sanitize_terminal_text
from hpc_gui.ssh.text import decode_remote_text


def run_ssh_command(
    client,
    command: str,
    *,
    log: Callable[[str], None],
    timeout_s: Optional[float] = None,
    connection_timeout: Optional[float] = None,
    log_output: bool = True,
) -> tuple[int, str, str]:
    """Run a command with bounded reads and secret-safe diagnostic logging."""
    if client is None:
        raise RuntimeError("SSH client not connected")
    started = timed()
    if is_sensitive_command(command):
        log("SSH$ <redacted>")
    else:
        log(f"SSH$ {command}")
    _stdin, stdout, stderr = client.exec_command(command)
    if timeout_s is None:
        timeout_s = connection_timeout
    if timeout_s is not None:
        try:
            stdout.channel.settimeout(timeout_s)
            stderr.channel.settimeout(timeout_s)
        except Exception:
            pass
    try:
        output = decode_remote_text(stdout.read())
        error = decode_remote_text(stderr.read())
        code = stdout.channel.recv_exit_status()
        timed_out = False
    except socket.timeout:
        output = ""
        error = ""
        code = 124
        timed_out = True
    if log_output and output.strip():
        log(_sanitize_terminal_text(output).rstrip("\n"))
    if log_output and error.strip():
        log("STDERR:\n" + _sanitize_terminal_text(error).rstrip("\n"))
    duration = timed() - started
    if timed_out:
        log(f"[timeout after {duration:.1f}s exit={code}]")
    else:
        log(f"[exit={code} duration={duration:.2f}s]")
    return code, output, error
