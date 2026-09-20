"""Framework-neutral connection state and authentication requests."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import count
from threading import Event
from typing import Any, Callable


_session_generation_counter = count(1)


class ConnectionState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    CONNECTED = "connected"
    FAILED = "failed"
    DISCONNECTING = "disconnecting"


@dataclass(frozen=True)
class HostKeyRequest:
    hostname: str
    fingerprint: str
    role: str = "target"
    # Public key algorithm (e.g. "ssh-ed25519"); shown in the trust prompt so
    # the user can verify what the server actually offered. Never a secret.
    key_type: str = ""


@dataclass(frozen=True)
class KeyboardInteractiveRequest:
    title: str
    instructions: str
    prompts: tuple[str, ...]
    # Optional for compatibility with existing callers; wx uses this to
    # preserve echo/no-echo semantics for each prompt.
    echo: tuple[bool, ...] = ()


class ConnectionController:
    """State machine; Qt adapters provide UI callbacks and SSH workers."""

    def __init__(self, emit: Callable[[ConnectionState], None] | None = None) -> None:
        self.state = ConnectionState.DISCONNECTED
        self.session: dict[str, Any] | None = None
        self.cancel_token = Event()
        self._emit = emit

    def transition(self, state: ConnectionState) -> None:
        self.state = state
        if self._emit:
            self._emit(state)

    def begin_connect(self) -> None:
        self.cancel_token.clear()
        self.transition(ConnectionState.CONNECTING)

    def begin_authentication(self) -> None:
        self.transition(ConnectionState.AUTHENTICATING)

    def finish(self, session: dict[str, Any]) -> None:
        # Every successful connect/reconnect mints a fresh session identity
        # so stale reader callbacks and superseded transports can be told
        # apart from the live session (RECON-007/CONN-006).
        session.setdefault("session_generation", next(_session_generation_counter))
        self.session = session
        self.transition(ConnectionState.CONNECTED)

    def fail(self) -> None:
        self.session = None
        self.transition(ConnectionState.FAILED)

    def cancel_connect(self) -> None:
        self.cancel_token.set()
        self.session = None
        self.transition(ConnectionState.DISCONNECTED)

    def begin_disconnect(self) -> None:
        self.transition(ConnectionState.DISCONNECTING)

    def finish_disconnect(self) -> None:
        self.session = None
        self.transition(ConnectionState.DISCONNECTED)


def close_session(session: Any) -> None:
    """Best-effort teardown of a superseded live session.

    Sessions produced by the wx/Qt adapters are dicts carrying the live
    ``ssh`` wrapper under ``"ssh"``. Reconnect must never orphan that
    wrapper: an orphaned client keeps its transport, shell reader thread
    and SFTP channels alive and queued UI actions could otherwise keep
    executing against the old session. Failures are swallowed because
    teardown runs on best-effort paths (reconnect supersede, logout).
    """
    if not isinstance(session, dict):
        return
    ssh = session.get("ssh")
    if ssh is None:
        return
    try:
        close = getattr(ssh, "close", None)
        if callable(close):
            close()
    except Exception:
        pass


def wipe_secret(value: Any) -> None:
    """Best-effort wipe for mutable secret buffers owned by an adapter."""
    if isinstance(value, (bytearray, list)):
        value[:] = [0] * len(value)


__all__ = [
    "ConnectionController", "ConnectionState", "HostKeyRequest",
    "KeyboardInteractiveRequest", "close_session", "wipe_secret",
]
