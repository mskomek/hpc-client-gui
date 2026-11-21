"""Open Paramiko interactive shells with X11 requested before the PTY/shell."""

from __future__ import annotations

from typing import Callable

from hpc_gui.ssh.contracts import _SSH_CHANNEL_TIMEOUT_SECONDS
from hpc_gui.ssh.errors import X11Unavailable
from hpc_gui.ssh.x11_forward import X11Forwarder


def open_x11_shell(
    client,
    *,
    log: Callable[[str], None],
    timeout: float | None = None,
    **pty_options,
):
    """Return ``(channel, forwarder)`` after an authenticated X11 shell opens."""
    trusted = bool(pty_options.pop("x11_trusted", False))
    try:
        forwarder = X11Forwarder(log=log, trusted=trusted)
    except Exception as exc:
        raise X11Unavailable(str(exc)) from exc
    try:
        probe = forwarder.display.connect(timeout=3.0)
        probe.close()
    except Exception as exc:
        forwarder.close()
        raise X11Unavailable("local X server is unavailable") from exc

    try:
        transport = client.get_transport()
        active = transport is not None and transport.is_active()
    except Exception as exc:
        forwarder.close()
        raise X11Unavailable("SSH transport could not be inspected") from exc
    if not active:
        forwarder.close()
        raise X11Unavailable("SSH transport is inactive")
    channel = None
    try:
        channel = transport.open_session(timeout=timeout)
        forwarder.request(channel)
    except Exception as exc:
        forwarder.close()
        if channel is not None:
            channel.close()
        raise X11Unavailable("local cookie missing or SSH forwarding refused") from exc

    try:
        channel.get_pty(**pty_options)
        channel.invoke_shell()
        return channel, forwarder
    except Exception:
        forwarder.close()
        channel.close()
        raise


class X11ShellController:
    """Own X11 shell setup and relay cleanup for one SSH client wrapper."""

    def __init__(self, *, log: Callable[[str], None]) -> None:
        self._log = log
        self._forwarder: X11Forwarder | None = None

    def invoke_shell(self, client, info, pty_options: dict):
        if info is not None and bool(getattr(info, "x11_forwarding", False)):
            try:
                channel, forwarder = open_x11_shell(
                    client,
                    log=self._log,
                    timeout=getattr(info, "timeout", None)
                    or _SSH_CHANNEL_TIMEOUT_SECONDS,
                    x11_trusted=bool(getattr(info, "x11_trusted", False)),
                    **pty_options,
                )
            except X11Unavailable as exc:
                self._log(f"SSH: X11 forwarding unavailable; connection refused ({exc})")
                raise
            else:
                self._forwarder = forwarder
                return channel
        return client.invoke_shell(**pty_options)

    def close(self) -> None:
        forwarder = self._forwarder
        self._forwarder = None
        if forwarder is not None:
            try:
                forwarder.close()
            except Exception:
                pass
