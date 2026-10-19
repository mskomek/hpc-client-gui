from __future__ import annotations

import getpass
import sys
from dataclasses import dataclass
from typing import Any

from hpc_gui.config.storage import load_profiles, load_settings, update_settings
from hpc_gui.core import secret_store
from hpc_gui.services.connection_profile_service import (
    AUTH_METHOD_KEYBOARD_INTERACTIVE,
    normalize_auth_methods,
    resolve_password_for_connect,
)
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


def _master_password_prompt_factory():
    """Resolve the app master password from DPAPI or a hidden CLI prompt."""
    cache = {"value": ""}

    def ask_master(_confirm: bool = False) -> str | None:
        if cache["value"]:
            return cache["value"]
        try:
            token = load_settings().get("master_password_dpapi")
        except Exception:
            token = None
        if token and secret_store.is_available():
            try:
                cache["value"] = secret_store.unprotect_secret(str(token))
                return cache["value"]
            except Exception:
                try:
                    update_settings({"master_password_dpapi": ""})
                except Exception:
                    pass
        if not sys.stdin.isatty() or not sys.stderr.isatty():
            raise RuntimeError("master_prompt_requires_terminal")
        try:
            value = getpass.getpass("Application master password: ")
        except (EOFError, KeyboardInterrupt):
            return None
        if not value:
            return None
        cache["value"] = value
        return value

    ask_master._cache = cache  # type: ignore[attr-defined]
    return ask_master


def _resolve_saved_profile_password(profile: dict[str, Any]) -> str:
    secret_fields = (
        "password_keychain_ref",
        "password_dpapi",
        "password_enc",
        "password_salt",
    )
    if "save_password" not in profile and any(profile.get(key) for key in secret_fields):
        # Older CLI profiles relied on the credential field itself as the
        # opt-in. Preserve that behavior while honoring an explicit opt-out.
        profile = dict(profile, save_password=True)
    try:
        return resolve_password_for_connect(
            profile,
            ask_master=_master_password_prompt_factory(),
        ) or ""
    except RuntimeError as exc:
        messages = {
            "master_cancelled": "Unlocking the saved profile password was cancelled.",
            "master_wrong": "Could not unlock the saved profile password; check the application master password.",
            "saved_password_unavailable": "The saved profile password is unavailable; re-save it in the GUI connection profile.",
            "master_prompt_requires_terminal": (
                "The saved profile password needs the application master password. "
                "Run this command in an interactive terminal, or use --password-prompt "
                "to enter the SSH password directly."
            ),
        }
        raise CLIConnectionError(messages.get(str(exc), "Could not resolve the saved profile password.")) from None


def _keyboard_interactive_handler(password: str):
    """Answer password prompts from the profile and prompt for other factors."""
    def answer(title: str, instructions: str, prompts: list[tuple[str, bool]]) -> list[str]:
        if not sys.stdin.isatty() or not sys.stderr.isatty():
            return []
        if title:
            print(title, file=sys.stderr)
        if instructions:
            print(instructions, file=sys.stderr)
        answers: list[str] = []
        for prompt, echo in prompts:
            label = f"{prompt.rstrip()} "
            lowered = prompt.lower()
            if password and ("password" in lowered or "passphrase" in lowered):
                answers.append(password)
            elif echo:
                answers.append(input(label))
            else:
                answers.append(getpass.getpass(label))
        return answers

    return answer


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
    elif profile and not getattr(args, "no_saved_password", False):
        keychain_ref = profile.get("password_keychain_ref")
        if not key_path and keychain_ref and secret_store.keychain_available():
            try:
                password = secret_store.unprotect_keychain_secret(str(keychain_ref))
            except Exception:
                password = ""
        elif not key_path and profile.get("password_dpapi") and secret_store.is_available():
            try:
                password = secret_store.unprotect_secret(str(profile["password_dpapi"]))
            except Exception:
                password = ""
        elif (
            profile.get("password_enc")
            and profile.get("password_salt")
            and (not key_path or not getattr(args, "key_path", ""))
        ):
            password = _resolve_saved_profile_password(profile)
    timeout = getattr(args, "timeout", None)
    keepalive_interval_seconds = coerce_keepalive_interval(
        (profile or {}).get("keepalive_interval_seconds", 30)
    )
    keyboard_interactive_handler = None
    if profile:
        auth_methods = normalize_auth_methods(profile.get("system"))
        if not auth_methods or AUTH_METHOD_KEYBOARD_INTERACTIVE in auth_methods:
            keyboard_interactive_handler = _keyboard_interactive_handler(password)

    return SSHConnInfo(
        host=host,
        port=port,
        username=username,
        password=password,
        key_path=key_path,
        host_key_policy=host_key_policy,
        timeout=timeout,
        keepalive_interval_seconds=keepalive_interval_seconds,
        keyboard_interactive_handler=keyboard_interactive_handler,
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
            if shell_output_cb is not None:
                ssh.activate_shell_output()
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
