"""wx packaged SSH smoke session wiring."""
from __future__ import annotations

import os


def _create_packaged_smoke_session(*, host=None, port=None, username=None, profile_name=None):
    """Create the smoke transport and session without touching wx state."""
    host = host if host else os.environ.get("HPC_GUI_PACKAGED_SMOKE_SSH_HOST", "").strip()
    if not host:
        return None
    try:
        port = int(port) if port not in (None, "") else int(os.environ["HPC_GUI_PACKAGED_SMOKE_SSH_PORT"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("packaged smoke SSH port is invalid") from exc
    username = username if username else os.environ.get("HPC_GUI_PACKAGED_SMOKE_SSH_USER", "").strip()
    password = os.environ.get("HPC_GUI_PACKAGED_SMOKE_SSH_PASSWORD", "")
    known_hosts = os.environ.get("HPC_GUI_PACKAGED_SMOKE_SSH_KNOWN_HOSTS", "").strip()
    if not username or not password or not known_hosts:
        raise RuntimeError("packaged smoke SSH environment is incomplete")

    from hpc_gui.services.files_ssh import SSHFilesBackend
    from hpc_gui.services.slurm_ssh import SSHSlurmBackend
    from hpc_gui.ssh.client import SSHClientWrapper, SSHConnInfo

    output_subscribers = []
    ssh = SSHClientWrapper(
        SSHConnInfo(
            host=host,
            port=port,
            username=username,
            password=password,
            known_hosts_path=known_hosts,
            host_key_policy="accept-new",
            host_key_decision=lambda _info: "save",
        ),
        shell_output_cb=lambda text: [callback(text) for callback in tuple(output_subscribers)],
    )
    ssh._wx_output_subscribers = output_subscribers  # type: ignore[attr-defined]
    try:
        ssh.connect(shell_size=(96, 31))
        profile = {
            "name": profile_name or "packaged-smoke",
            "host": host,
            "port": port,
            "username": username,
            "system": {},
        }
        return {
            "connected": True,
            "ssh": ssh,
            "files": SSHFilesBackend(ssh),
            "slurm": SSHSlurmBackend(ssh, profile.get("system") or {}),
            "profile_name": profile["name"],
            "profile": profile,
            "output_subscribers": output_subscribers,
        }
    except Exception:
        ssh.close()
        raise


def _attach_packaged_smoke_session(session_state, frame, lifecycle, session):
    """Attach a created session to wx widgets on the GUI thread."""
    import wx

    if not wx.IsMainThread():
        raise RuntimeError("packaged smoke session must attach on the wx GUI thread")
    from hpc_gui.wx_shell_connections import _connection_callbacks

    _connection_callbacks(session_state, frame, lifecycle)["on_connected"](session)
    return session


def _connect_packaged_smoke_session(session_state, frame, lifecycle, *, host=None, port=None,
                                      username=None, profile_name=None):
    """Compatibility composition for smoke flows already running on GUI thread."""
    session = _create_packaged_smoke_session(
        host=host, port=port, username=username, profile_name=profile_name,
    )
    if session is not None:
        _attach_packaged_smoke_session(session_state, frame, lifecycle, session)
    return session
