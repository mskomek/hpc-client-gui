"""wx packaged SSH smoke session wiring"""
from __future__ import annotations

from hpc_gui.wx_shell_connections import _connection_callbacks
import os


def _connect_packaged_smoke_session(session_state, frame, lifecycle, *, host=None, port=None, username=None,
                                      profile_name=None):
    """Attach the parent smoke runner's disposable SSH server to the frame.

    Explicit ``host``/``port``/``username`` overrides let the fresh-user
    acceptance connect through the endpoint stored in the GUI-created
    profile instead of the raw parent environment; secrets always come from
    the parent environment and are never persisted.
    """
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
        session = {
            "connected": True,
            "ssh": ssh,
            "files": SSHFilesBackend(ssh),
            "slurm": SSHSlurmBackend(ssh, profile.get("system") or {}),
            "profile_name": profile["name"],
            "profile": profile,
            "output_subscribers": output_subscribers,
        }
        session_state["session"] = session
        session_state["generation"] = session_state.get("generation", 0) + 1
        _connection_callbacks(session_state, frame, lifecycle)["on_connected"](session)
        lifecycle.register_cleanup(ssh.close)
        return session
    except Exception:
        ssh.close()
        raise
