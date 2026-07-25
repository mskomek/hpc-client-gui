from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any

from truba_gui.config.storage import load_profiles
from truba_gui.services.files_ssh import SSHFilesBackend
from truba_gui.ssh.client import SSHClientWrapper, SSHConnInfo


class CLIConnectionError(RuntimeError):
    """A user-actionable CLI connection failure."""


@dataclass
class CLISession:
    ssh: SSHClientWrapper
    files: SSHFilesBackend
    profile_name: str = ""

    @classmethod
    def open(cls, args) -> "CLISession":
        profile = None
        profile_name = str(getattr(args, "profile", "") or "").strip()
        if profile_name:
            profile = next(
                (item for item in load_profiles() if item.get("name") == profile_name),
                None,
            )
            if profile is None:
                raise CLIConnectionError(f"Profile not found: {profile_name}")

        host = str(getattr(args, "host", "") or (profile or {}).get("host", "")).strip()
        if not host:
            raise CLIConnectionError("A host or --profile is required.")
        try:
            port = int(getattr(args, "port", None) or (profile or {}).get("port", 22) or 22)
        except (TypeError, ValueError) as exc:
            raise CLIConnectionError("Port must be numeric.") from exc
        username = str(getattr(args, "username", "") or (profile or {}).get("username", ""))
        key_path = str(getattr(args, "key_path", "") or (profile or {}).get("key_path", ""))
        host_key_policy = "strict" if getattr(args, "strict_host_key", False) else str(
            (profile or {}).get("host_key_policy", "accept-new") or "accept-new"
        )
        password = ""
        if getattr(args, "password_stdin", False):
            password = sys.stdin.readline().rstrip("\r\n")

        info = SSHConnInfo(
            host=host,
            port=port,
            username=username,
            password=password,
            key_path=key_path,
            host_key_policy=host_key_policy,
        )
        ssh = SSHClientWrapper(info=info)
        try:
            ssh.connect()
            files = SSHFilesBackend(ssh)
        except Exception as exc:
            try:
                ssh.close()
            except Exception:
                pass
            raise CLIConnectionError(f"SSH/SFTP connection failed: {exc}") from exc
        return cls(ssh=ssh, files=files, profile_name=profile_name)

    def close(self) -> None:
        self.ssh.close()
