from __future__ import annotations

import getpass
import sys
from dataclasses import dataclass
from typing import Any

from hpc_gui.config.storage import load_profiles
from hpc_gui.core import secret_store
from hpc_gui.services.files_ssh import SSHFilesBackend
from hpc_gui.services.files_ftp import FTPFilesBackend
from hpc_gui.ssh.client import SSHClientWrapper, SSHConnInfo, coerce_keepalive_interval


def resolve_profile(name: str) -> dict[str, Any] | None:
    """Return the saved profile record for an exact name, or None."""
    return next(
        (item for item in load_profiles() if item.get("name") == name),
        None,
    )


def effective_profile_name(args) -> str:
    """Return the explicit --profile value, or the saved CLI default profile."""
    explicit = str(getattr(args, "profile", "") or "").strip()
    if explicit:
        return explicit
    from hpc_gui.config.storage import get_cli_default_profile

    return get_cli_default_profile()


def build_ssh_conn_info(args) -> SSHConnInfo:
    """Resolve CLI args (and an optional profile) into an ``SSHConnInfo``.

    Raises ``CLIConnectionError`` for a missing host, an invalid port, or a
    requested profile that does not exist.
    """
    profile = None
    profile_name = effective_profile_name(args)
    if profile_name:
        profile = resolve_profile(profile_name)
        if profile is None:
            raise CLIConnectionError(f"Profile not found: {profile_name}")
        if not profile.get("cli_allowed", False):
            raise CLIConnectionError(
                f"Profile '{profile_name}' is not allowed for CLI use. "
                "Enable it in the connection's edit dialog."
            )

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
    if getattr(args, "password_stdin", False) and getattr(args, "password_prompt", False):
        raise CLIConnectionError("Use only one of --password-stdin or --password-prompt.")
    if getattr(args, "password_stdin", False):
        password = sys.stdin.readline().rstrip("\r\n")
    elif getattr(args, "password_prompt", False):
        if not sys.stdin.isatty() or not sys.stderr.isatty():
            raise CLIConnectionError("--password-prompt requires an interactive terminal; use --password-stdin for automation.")
        password = getpass.getpass("SSH password: ")
    elif (
        profile
        and not key_path
        and not getattr(args, "no_saved_password", False)
        and secret_store.is_available()
    ):
        saved_token = profile.get("password_dpapi")
        if saved_token:
            try:
                password = secret_store.unprotect_secret(str(saved_token))
            except Exception:
                password = ""
    timeout = getattr(args, "timeout", None)
    keepalive_interval_seconds = coerce_keepalive_interval(
        (profile or {}).get("keepalive_interval_seconds", 30)
    )

    return SSHConnInfo(
        host=host,
        port=port,
        username=username,
        password=password,
        key_path=key_path,
        host_key_policy=host_key_policy,
        timeout=timeout,
        keepalive_interval_seconds=keepalive_interval_seconds,
    )


class CLIConnectionError(RuntimeError):
    """A user-actionable CLI connection failure."""


@dataclass
class CLISession:
    ssh: SSHClientWrapper | None
    files: SSHFilesBackend | FTPFilesBackend
    profile_name: str = ""

    @classmethod
    def open(cls, args) -> "CLISession":
        info = build_ssh_conn_info(args)
        if getattr(args, "transport", "sftp") == "ftp":
            if getattr(args, "group", None) != "files":
                raise CLIConnectionError("FTP transport supports file commands only; use --transport sftp for SSH/Slurm commands.")
            if info.key_path:
                raise CLIConnectionError("FTP transport does not use an SSH key.")
            try:
                files = FTPFilesBackend(
                    info.host,
                    port=int(getattr(args, "port", None) or 21),
                    username=info.username,
                    password=info.password,
                    timeout=float(info.timeout or 20),
                )
            except Exception as exc:
                raise CLIConnectionError(f"FTP connection failed: {exc}") from exc
            return cls(ssh=None, files=files, profile_name=str(getattr(args, "profile", "") or "").strip())
        logger: Any = None
        if getattr(args, "verbose", False):

            def verbose_log(message: str) -> None:
                print(f"[debug] {message}", file=sys.stderr)

            logger = verbose_log
        shell_output_cb = None
        if getattr(args, "group", None) == "terminal":
            def shell_output_cb(text: str) -> None:
                sys.stdout.write(text)
                sys.stdout.flush()

        ssh = SSHClientWrapper(info=info, logger=logger, shell_output_cb=shell_output_cb)
        try:
            ssh.connect()
            files = SSHFilesBackend(ssh)
        except Exception as exc:
            try:
                ssh.close()
            except Exception:
                pass
            raise CLIConnectionError(f"SSH/SFTP connection failed: {exc}") from exc
        profile_name = str(getattr(args, "profile", "") or "").strip()
        return cls(ssh=ssh, files=files, profile_name=profile_name)

    def close(self) -> None:
        close_files = getattr(self.files, "close", None)
        if close_files:
            close_files()
        if self.ssh is not None:
            self.ssh.close()
