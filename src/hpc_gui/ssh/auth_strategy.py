"""SSH authentication sources and server-method-aware strategy."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import paramiko
from paramiko.auth_strategy import (
    AuthFailure,
    AuthResult,
    AuthSource,
    AuthStrategy,
    InMemoryPrivateKey,
    OnDiskPrivateKey,
    SourceResult,
)


class NoAuthenticationCredentialError(paramiko.SSHException):
    """No credential/source was available to authenticate at all."""

    def __init__(self) -> None:
        super().__init__(
            "No authentication credential is available for this connection. "
            "Enter a password, configure an SSH key, or enable an applicable "
            "authentication method."
        )


def load_private_key_with_certificate(key_path: str, password: str | None = None):
    """Load a private key and its conventional sibling OpenSSH certificate."""
    if password:
        pkey = paramiko.PKey.from_path(key_path, password)
    else:
        pkey = paramiko.PKey.from_path(key_path)
    certificate_path = Path(key_path).with_name(Path(key_path).name + "-cert.pub")
    if certificate_path.is_file():
        pkey.load_certificate(str(certificate_path))
    return pkey


def _agent_key_sources(username: str):
    """Yield in-memory sources for keys offered by a running ssh-agent."""
    try:
        keys = list(paramiko.Agent().get_keys())
    except Exception:
        return
    for key in keys:
        yield InMemoryPrivateKey(username, key)


def _discoverable_key_sources(username: str, password: str):
    """Yield conventional ~/.ssh keys Paramiko would otherwise discover."""
    candidates = [
        Path.home() / directory / name
        for directory in (".ssh", "ssh")
        for name in ("id_rsa", "id_ecdsa", "id_ed25519")
    ]
    seen: set[str] = set()
    for key_path in candidates:
        path_key = str(key_path)
        if path_key in seen or not key_path.is_file():
            continue
        seen.add(path_key)
        try:
            pkey = load_private_key_with_certificate(path_key, password or None)
        except Exception:
            continue
        yield OnDiskPrivateKey(username, "implicit-home", key_path, pkey)


class _KeyboardInteractiveSource(AuthSource):
    def __init__(self, username, handler):
        super().__init__(username)
        self.handler = handler

    def __repr__(self):
        return self._repr(user=self.username)

    def authenticate(self, transport):
        return transport.auth_interactive(self.username, self.handler)


class _PasswordSource(AuthSource):
    def __init__(self, username, password_getter):
        super().__init__(username)
        self.password_getter = password_getter

    def __repr__(self):
        return self._repr(user=self.username)

    def authenticate(self, transport):
        return transport.auth_password(self.username, self.password_getter())


def _source_method(source) -> str | None:
    if isinstance(source, (InMemoryPrivateKey, OnDiskPrivateKey)):
        return "publickey"
    if isinstance(source, _PasswordSource):
        return "password"
    if isinstance(source, _KeyboardInteractiveSource):
        return "keyboard-interactive"
    return None


class _ConnectionAuthStrategy(AuthStrategy):
    """Offer configured credentials only for methods accepted by the server."""

    def __init__(
        self,
        info: Any,
        pkey=None,
        *,
        agent_key_sources=_agent_key_sources,
        discoverable_key_sources=_discoverable_key_sources,
    ):
        super().__init__(ssh_config=None)
        self.info = info
        self.pkey = pkey
        self.agent_key_sources = agent_key_sources
        self.discoverable_key_sources = discoverable_key_sources

    def get_sources(self):
        username = self.info.username
        if self.pkey is not None:
            yield InMemoryPrivateKey(username, self.pkey)
        if getattr(self.info, "allow_agent", True):
            yield from self.agent_key_sources(username)
        if getattr(self.info, "look_for_keys", True):
            yield from self.discoverable_key_sources(username, self.info.password)
        if self.info.password:
            yield _PasswordSource(username, lambda: self.info.password)
        if self.info.keyboard_interactive_handler is not None:
            yield _KeyboardInteractiveSource(
                username, self.info.keyboard_interactive_handler
            )

    def _probe_allowed_methods(self, transport) -> tuple[str, ...] | None:
        """Ask SSH which methods it permits without sending a credential."""
        probe = getattr(transport, "auth_none", None)
        if not callable(probe):
            return None
        try:
            return tuple(probe(self.info.username) or ())
        except paramiko.BadAuthenticationType as exc:
            return tuple(getattr(exc, "allowed_types", ()) or ())
        except Exception:
            return None

    def authenticate(self, transport):
        overall_result = AuthResult(strategy=self)
        allowed_methods = self._probe_allowed_methods(transport)
        if allowed_methods == ():
            is_authenticated = getattr(transport, "is_authenticated", None)
            if callable(is_authenticated) and is_authenticated():
                return overall_result

        for source in self.get_sources():
            method = _source_method(source)
            if allowed_methods is not None and method and method not in allowed_methods:
                continue
            try:
                result = source.authenticate(transport)
            except paramiko.BadAuthenticationType as exc:
                overall_result.append(SourceResult(source, exc))
                allowed_methods = tuple(getattr(exc, "allowed_types", ()) or ())
                continue
            except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
                overall_result.append(SourceResult(source, exc))
                continue
            overall_result.append(SourceResult(source, result))
            if not result:
                return overall_result
            # A non-empty result means partial auth; only those methods remain.
            allowed_methods = tuple(result)
        raise AuthFailure(result=overall_result)
