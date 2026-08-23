from __future__ import annotations

import errno
import socket
from typing import Optional

import paramiko

from hpc_gui.core.debug_support import log_exception_with_id, new_error_id
from hpc_gui.core.i18n import t


def describe_connection_error(exc: BaseException, fallback: str = "") -> str:
    """Return an actionable, localized explanation for common connection failures."""

    causes = list(getattr(exc, "errors", {}).values()) or [exc]
    text = (fallback or str(exc)).strip()
    lowered = text.lower()

    # Jump-host stages get distinct, actionable messages.
    from hpc_gui.ssh.jump import (
        JumpAuthenticationError,
        JumpConnectionError,
        JumpForwardingDeniedError,
    )

    if isinstance(exc, JumpAuthenticationError):
        key = "connection.jump_error_auth"
    elif isinstance(exc, JumpForwardingDeniedError):
        key = "connection.jump_error_forwarding"
    elif isinstance(exc, JumpConnectionError):
        key = "connection.jump_error_connect"
    elif isinstance(exc, (paramiko.AuthenticationException, paramiko.PasswordRequiredException)) or any(
        phrase in lowered
        for phrase in ("authentication failed", "auth failed", "no authentication methods")
    ):
        key = "connection.error_authentication"
    elif isinstance(exc, (FileNotFoundError, PermissionError)):
        key = "connection.error_key_file"
    elif any(isinstance(cause, socket.gaierror) for cause in causes):
        key = "connection.error_dns"
    elif any(isinstance(cause, ConnectionRefusedError) or getattr(cause, "errno", None) in (errno.ECONNREFUSED, 10061) for cause in causes):
        key = "connection.error_refused"
    elif any(isinstance(cause, (TimeoutError, socket.timeout)) or getattr(cause, "errno", None) in (errno.ETIMEDOUT, 10060) for cause in causes):
        key = "connection.error_timeout"
    elif any(isinstance(cause, (ConnectionResetError, BrokenPipeError, EOFError)) for cause in causes):
        key = "connection.error_reset"
    elif "banner" in lowered:
        key = "connection.error_banner"
    elif "key-exchange" in lowered or "key exchange" in lowered or "kex" in lowered:
        key = "connection.error_handshake"
    elif "private key" in lowered or "key file" in lowered or "not a valid" in lowered:
        key = "connection.error_key_file"
    elif isinstance(exc, paramiko.SSHException):
        key = "connection.error_protocol"
    else:
        key = "connection.error_unreachable"

    explanation = t(key)
    if text and text not in explanation:
        explanation += f"\n\n{t('common.technical_detail')}: {text}"
    return explanation


def show_exception(
    parent,
    *,
    title: Optional[str] = None,
    user_message: Optional[str] = None,
    exc: Optional[BaseException] = None,
    area: str = "GEN",
) -> None:
    try:
        from PySide6.QtWidgets import QMessageBox
    except Exception:
        return

    if exc is not None:
        err_id = log_exception_with_id(area, exc)
    else:
        err_id = new_error_id(area)

    ttl = title or t("common.error")
    label = t("common.error_code")
    hint = t("common.error_code_hint")
    msg = (user_message or t("common.error")) + f"\n\n{label}: {err_id}\n{hint}"
    QMessageBox.critical(parent, ttl, msg)
