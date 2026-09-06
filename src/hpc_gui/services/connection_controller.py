"""Framework-neutral connection state and authentication requests."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from threading import Event
from typing import Any, Callable


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


def wipe_secret(value: Any) -> None:
    """Best-effort wipe for mutable secret buffers owned by an adapter."""
    if isinstance(value, (bytearray, list)):
        value[:] = [0] * len(value)


__all__ = [
    "ConnectionController", "ConnectionState", "HostKeyRequest",
    "KeyboardInteractiveRequest", "wipe_secret",
]
