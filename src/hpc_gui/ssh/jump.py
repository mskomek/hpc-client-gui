"""One-hop SSH jump host (bastion) support.

Opens a ``direct-tcpip`` channel through the jump host that is handed to
the target ``SSHClient.connect(sock=...)`` via the existing
``preconnected_socket`` hook. The jump client/channel are owned by
:class:`JumpConnection` and must be cleaned up by the target wrapper.

No passwords are stored or reused for the jump host: v1 expects key or
SSH-agent authentication.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

import paramiko

from hpc_gui.config.jump_host_profile import normalize_jump_host_settings
from hpc_gui.ssh.client import (
    HostKeyChangedError,
    HostKeyRejectedError,
    _KnownHostsPolicy,
    coerce_keepalive_interval,
    load_private_key_with_certificate,
)


class JumpConnectionError(paramiko.SSHException):
    """Jump host connect/network/timeout failure."""


class JumpAuthenticationError(paramiko.SSHException):
    """Jump host authentication failed (v1 expects key/agent auth)."""


class JumpForwardingDeniedError(paramiko.SSHException):
    """The jump host refused the direct-tcpip channel."""


@dataclass(frozen=True)
class SSHJumpInfo:
    """Typed runtime jump configuration consumed by the SSH layer."""

    enabled: bool = False
    host: str = ""
    port: int = 22
    username: str = ""
    key_path: str = ""
    host_key_policy: str = "accept-new"
    keepalive_interval_seconds: int = 30


def jump_info_from_settings(value: object) -> Optional[SSHJumpInfo]:
    """Build typed runtime info from persisted settings; None if unused."""
    normalized = normalize_jump_host_settings(value)
    if not normalized.get("enabled") or not normalized.get("host"):
        return None
    return SSHJumpInfo(
        enabled=True,
        host=str(normalized["host"]),
        port=int(normalized["port"]),
        username=str(normalized["username"]),
        key_path=str(normalized["key_path"]),
        host_key_policy=str(normalized["host_key_policy"]),
    )


@dataclass
class JumpConnection:
    """Owns the jump SSHClient and its direct-tcpip channel."""

    info: SSHJumpInfo
    target_host: str
    target_port: int
    known_hosts_path: str = ""
    host_key_decision: Optional[Callable[[Any], str]] = None
    log: Optional[Callable[[str], None]] = None
    client: Optional[paramiko.SSHClient] = field(default=None, repr=False)
    channel: object = field(default=None, repr=False)

    def _log(self, message: str) -> None:
        if self.log:
            try:
                self.log(message)
            except Exception:
                pass

    def open(self):
        """Connect to the jump host and open the forwarded channel.

        Returns a socket-like Paramiko channel for the target connect.
        Raises stage-specific errors; partial resources are closed.
        """
        identity = (
            f"{self.info.username}@{self.info.host}"
            if self.info.username
            else self.info.host
        )
        self._log(f"SSH: connecting to jump {identity}:{self.info.port}")
        client = paramiko.SSHClient()
        self.client = client
        known_hosts_path = Path(self.known_hosts_path) if self.known_hosts_path else None
        try:
            client.load_system_host_keys()
            if known_hosts_path is not None and known_hosts_path.exists():
                client.load_host_keys(str(known_hosts_path))
            policy = (self.info.host_key_policy or "accept-new").strip().lower()
            if policy == "strict":
                client.set_missing_host_key_policy(paramiko.RejectPolicy())
                self._log("SSH: jump host key policy = strict")
            else:
                client.set_missing_host_key_policy(
                    _KnownHostsPolicy(
                        known_hosts_path or Path(""), self.host_key_decision, role="jump"
                    )
                )
                self._log("SSH: jump host key policy = accept-new")

            timeout = 45.0
            try:
                if self.info.key_path:
                    pkey = load_private_key_with_certificate(self.info.key_path)
                    client.connect(
                        hostname=self.info.host,
                        port=self.info.port,
                        username=self.info.username or None,
                        pkey=pkey,
                        timeout=timeout,
                        banner_timeout=timeout,
                        auth_timeout=30.0,
                        allow_agent=True,
                        look_for_keys=True,
                    )
                else:
                    # No password reuse: agent / discoverable keys only.
                    client.connect(
                        hostname=self.info.host,
                        port=self.info.port,
                        username=self.info.username or None,
                        timeout=timeout,
                        banner_timeout=timeout,
                        auth_timeout=30.0,
                        allow_agent=True,
                        look_for_keys=True,
                    )
            except paramiko.AuthenticationException as exc:
                self.close()
                raise JumpAuthenticationError(
                    "Jump host authentication failed; v1 expects SSH key or "
                    "agent authentication for the jump host."
                ) from exc
            except paramiko.BadHostKeyException as exc:
                self.close()
                raise HostKeyChangedError(exc.hostname, role="jump") from exc
            except (
                paramiko.SSHException,
                OSError,
            ) as exc:
                self.close()
                if isinstance(exc, HostKeyRejectedError):
                    raise
                raise JumpConnectionError(
                    f"Jump host connection failed: {exc}"
                ) from exc

            transport = client.get_transport()
            if transport is None or not transport.is_active():
                self.close()
                raise JumpConnectionError("Jump host connection failed: no active transport")
            keepalive = coerce_keepalive_interval(self.info.keepalive_interval_seconds)
            transport.set_keepalive(keepalive)
            self._log("SSH: jump authenticated")

            self._log(
                f"SSH: opening direct-tcpip to {self.target_host}:{self.target_port}"
            )
            try:
                channel = transport.open_channel(
                    "direct-tcpip",
                    dest_addr=(self.target_host, self.target_port),
                    src_addr=("127.0.0.1", 0),
                )
            except paramiko.ChannelException as exc:
                self.close()
                raise JumpForwardingDeniedError(
                    "Jump host denied forwarding (direct-tcpip failed)."
                ) from exc
            if channel is None:
                self.close()
                raise JumpForwardingDeniedError(
                    "Jump host denied forwarding (direct-tcpip failed)."
                )
            self.channel = channel
            self._log("SSH: jump channel ready")
            return channel
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        """Idempotently close the forwarded channel then the jump client."""
        try:
            if self.channel is not None:
                try:
                    self.channel.close()
                except Exception:
                    pass
        finally:
            self.channel = None
        try:
            if self.client is not None:
                try:
                    self.client.close()
                except Exception:
                    pass
        finally:
            self.client = None
