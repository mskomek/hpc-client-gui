"""Shared contracts and timeouts for SSH client and jump connections."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Optional, Protocol

from hpc_gui.ssh.host_keys import HostKeyInfo

if TYPE_CHECKING:
    from hpc_gui.ssh.jump import SSHJumpInfo


class SocketLike(Protocol):
    """Minimal socket-like surface Paramiko needs for a preconnected channel."""

    def send(self, data: bytes) -> int: ...

    def recv(self, size: int) -> bytes: ...

    def settimeout(self, timeout: float | None) -> None: ...

    def close(self) -> None: ...


_SSH_CONNECT_AND_KEX_TIMEOUT_SECONDS = 45
_SSH_BANNER_TIMEOUT_SECONDS = 45
_SSH_AUTH_TIMEOUT_SECONDS = 30
_SSH_CHANNEL_TIMEOUT_SECONDS = 30
_KEEPALIVE_INTERVAL_DEFAULT = 30


def coerce_keepalive_interval(
    value: object, default: int = _KEEPALIVE_INTERVAL_DEFAULT
) -> int:
    """Return a profile interval clamped to 0..3600 seconds."""
    try:
        return max(0, min(3600, int(value)))  # type: ignore[arg-type]
    except (OverflowError, TypeError, ValueError):
        return default


@dataclass
class SSHConnInfo:
    host: str
    port: int
    username: str = ""
    # Never include the plaintext secret in a repr that may reach logs.
    password: str = field(default="", repr=False)
    key_path: str = ""
    host_key_policy: str = "accept-new"
    x11_forwarding: bool = False
    timeout: Optional[float] = None
    keepalive_interval_seconds: int = _KEEPALIVE_INTERVAL_DEFAULT
    known_hosts_path: str = ""
    host_key_decision: Optional[Callable[[HostKeyInfo], str]] = None
    preconnected_socket: Optional[SocketLike] = None
    jump: Optional["SSHJumpInfo"] = None
    keyboard_interactive_handler: Optional[
        Callable[[str, str, list[tuple[str, bool]]], list[str]]
    ] = None
    allow_agent: bool = True
    look_for_keys: bool = True
