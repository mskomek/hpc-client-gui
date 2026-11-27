"""Connection-scoped policy for the Settings transfer speed test."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hpc_gui.config.system_profile import format_remote_path, normalize_system_settings


@dataclass(frozen=True)
class TransferSpeedTarget:
    """Validated connection data captured before a background speed test."""

    session_state: dict[str, Any]
    session: dict[str, Any]
    files: Any
    generation: Any
    remote_dir: str


def resolve_transfer_speed_target(
    session_state: dict[str, Any] | None,
) -> TransferSpeedTarget:
    """Resolve an active SFTP-capable connection and its configured test path.

    This only reads in-memory session/profile data. The returned backend is
    used by the worker thread for all network and file I/O.
    """
    if not isinstance(session_state, dict):
        raise RuntimeError("No active connection is available for the speed test")
    if session_state.get("connection_status") != "connected":
        raise RuntimeError("No active connection is available for the speed test")

    session = session_state.get("session")
    if not isinstance(session, dict) or not session.get("connected"):
        raise RuntimeError("The active connection is not ready for file transfers")
    files = session.get("files")
    if files is None or not all(
        callable(getattr(files, method, None))
        for method in ("upload", "download", "remove")
    ):
        raise RuntimeError("The active connection does not support SFTP file transfers")

    profile = session.get("profile")
    if not isinstance(profile, dict):
        raise RuntimeError("The active connection has no remote profile")
    system = profile.get("system")
    if not isinstance(system, dict):
        system = profile.get("system_settings")
    settings = normalize_system_settings(system)
    template = str(settings.get("scratch_dir") or settings.get("home_dir") or "").strip()
    username = str(profile.get("username") or profile.get("user") or "").strip()
    if not template:
        raise RuntimeError("The active profile has no scratch or home directory for a test file")
    if not username:
        raise RuntimeError("The active profile has no username for its remote test directory")

    remote_dir = format_remote_path(template, username).strip()
    if not remote_dir.startswith("/"):
        raise RuntimeError("The configured remote test directory must be an absolute path")
    return TransferSpeedTarget(
        session_state=session_state,
        session=session,
        files=files,
        generation=session_state.get("generation", 0),
        remote_dir=remote_dir,
    )


def transfer_speed_target_is_current(
    session_state: dict[str, Any] | None,
    target: TransferSpeedTarget,
) -> bool:
    """Reject a worker result after disconnect, reconnect, or session swap."""
    return bool(
        isinstance(session_state, dict)
        and session_state is target.session_state
        and session_state.get("connection_status") == "connected"
        and session_state.get("session") is target.session
        and session_state.get("generation", 0) == target.generation
        and target.session.get("connected")
    )


__all__ = [
    "TransferSpeedTarget",
    "resolve_transfer_speed_target",
    "transfer_speed_target_is_current",
]
