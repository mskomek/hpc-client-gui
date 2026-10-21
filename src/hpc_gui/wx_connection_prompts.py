"""Localized, secret-free prompts used by the wx connection controller."""

from __future__ import annotations

from hpc_gui.core.i18n import t
from hpc_gui.services.connection_controller import HostKeyRequest


def format_host_key_prompt(request: HostKeyRequest) -> str:
    """Render the unknown-host security prompt without exposing secrets."""
    role_label = (
        t("connection.host_key_role_jump")
        if request.role == "jump"
        else t("connection.host_key_role_target")
    )
    key_type = request.key_type or "SSH"
    return t("connection.host_key_prompt_message").format(
        role=role_label,
        host=request.hostname,
        key_type=key_type,
        fingerprint=request.fingerprint,
    )
