"""Known-host records, decisions, and policy for target and jump SSH links."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import paramiko


@dataclass(frozen=True)
class HostKeyInfo:
    hostname: str
    key_type: str
    fingerprint: str
    role: str = "target"


class HostKeyChangedError(paramiko.SSHException):
    def __init__(self, hostname: str, role: str = "target"):
        self.hostname = hostname
        self.role = role
        super().__init__(f"Host key changed for {hostname}; connection cancelled.")


class HostKeyRejectedError(paramiko.SSHException):
    def __init__(self, hostname: str, role: str = "target"):
        self.hostname = hostname
        self.role = role
        super().__init__(f"Unknown host key rejected for {hostname}.")


class _KnownHostsPolicy(paramiko.MissingHostKeyPolicy):
    def __init__(
        self,
        path: Path,
        decide: Callable[[HostKeyInfo], str] | None,
        role: str = "target",
    ) -> None:
        self.path = path
        self.decide = decide
        self.role = role

    def missing_host_key(self, client, hostname, key) -> None:
        fingerprint = getattr(key, "fingerprint", "") or key.get_fingerprint().hex()
        decision = self.decide(
            HostKeyInfo(hostname, key.get_name(), fingerprint, role=self.role)
        ) if self.decide else "save"
        if decision == "once":
            return
        if decision != "save":
            raise HostKeyRejectedError(hostname, role=self.role)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        client.get_host_keys().add(hostname, key.get_name(), key)
        client.save_host_keys(str(self.path))
        if os.name == "posix" and self.path.exists():
            self.path.chmod(0o600)


def configure_known_hosts(
    client: paramiko.SSHClient,
    path: Path,
    policy: str,
    decision: Callable[[HostKeyInfo], str] | None,
) -> str:
    """Load host-key stores and install the selected target policy."""
    client.load_system_host_keys()
    if path.exists():
        client.load_host_keys(str(path))
    normalized = (policy or "accept-new").strip().lower()
    if normalized == "strict":
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
    else:
        client.set_missing_host_key_policy(_KnownHostsPolicy(path, decision))
        normalized = "accept-new"
    return normalized
