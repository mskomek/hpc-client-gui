"""Remote command execution for the SSH client wrapper."""

from __future__ import annotations

import socket
from typing import Optional, Tuple

from hpc_gui.core.debug_support import timed
from hpc_gui.services.command_history_store import is_sensitive_command
from hpc_gui.ssh.shell_session import _sanitize_terminal_text
from hpc_gui.ssh.text import decode_remote_text as _decode_remote_text


class CommandExecutionMixin:
    """Run one remote command and log its outcome without leaking secrets."""

    def run(
        self,
        command: str,
        *,
        timeout_s: Optional[float] = None,
        log_output: bool = True,
    ) -> Tuple[int, str, str]:
        if not self.client:
            raise RuntimeError("SSH client not connected")
        t0 = timed()
        # Never echo secrets into the UI/logs.
        if is_sensitive_command(command):
            self.log("SSH$ <redacted>")
        else:
            self.log(f"SSH$ {command}")
        stdin, stdout, stderr = self.client.exec_command(command)
        if timeout_s is None and getattr(self.info, "timeout", None) is not None:
            timeout_s = self.info.timeout
        if timeout_s is not None:
            try:
                stdout.channel.settimeout(timeout_s)
                stderr.channel.settimeout(timeout_s)
            except Exception:
                pass
        try:
            out = _decode_remote_text(stdout.read())
            err = _decode_remote_text(stderr.read())
            code = stdout.channel.recv_exit_status()
            timed_out = False
        except socket.timeout:
            out = ""
            err = ""
            code = 124
            timed_out = True
        if log_output and out.strip():
            self.log(_sanitize_terminal_text(out).rstrip("\n"))
        if log_output and err.strip():
            self.log("STDERR:\n" + _sanitize_terminal_text(err).rstrip("\n"))
        dt = timed() - t0
        if timed_out:
            self.log(f"[timeout after {dt:.1f}s exit={code}]")
        else:
            self.log(f"[exit={code} duration={dt:.2f}s]")
        return code, out, err
