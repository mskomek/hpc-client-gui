"""Connection diagnostics for the ``doctor connection`` CLI flow.

This service is the single owner of the connection stage logic. It walks the
canonical stage set (``port``, ``auth``, ``sftp``, ``checksum``) and returns a
report dict. It never prints, never includes secrets, and keeps every stage
detail static so no host, username, key path, or raw exception text leaks out.
"""

from __future__ import annotations

import socket
from typing import Any, Callable, Optional

from truba_gui.ssh.client import SSHClientWrapper, SSHConnInfo


STAGES = ("port", "auth", "sftp", "checksum")


def _default_socket_connect(host: str, port: int, timeout: Optional[float]) -> bool:
    connection = socket.create_connection((host, port), timeout=timeout)
    connection.close()
    return True


def _default_ssh_factory(info: SSHConnInfo) -> SSHClientWrapper:
    wrapper = SSHClientWrapper(info)
    wrapper.connect()
    return wrapper


def _default_checksum_probe(wrapper: SSHClientWrapper) -> int:
    code, _out, _err = wrapper.run("command -v sha256sum")
    return code


def _sftp_available(wrapper: Any) -> bool:
    supports = getattr(wrapper, "supports_transfer_sftp_channels", None)
    if callable(supports):
        return bool(supports())
    opener = getattr(wrapper, "open_transfer_sftp", None)
    if callable(opener):
        channel = opener()
        try:
            channel.close()
        except Exception:
            pass
        return True
    return getattr(wrapper, "sftp", None) is not None


def run_connection_diagnostics(
    info: SSHConnInfo,
    *,
    socket_connect: Optional[Callable[..., Any]] = None,
    ssh_factory: Optional[Callable[..., Any]] = None,
    checksum_probe: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """Run the connection stage matrix and return the report payload.

    ``socket_connect(host, port, timeout)`` probes TCP reachability.
    ``ssh_factory(info)`` authenticates and returns a live wrapper.
    ``checksum_probe(wrapper)`` reports the remote checksum-tool exit code.
    """
    socket_connect = socket_connect or _default_socket_connect
    ssh_factory = ssh_factory or _default_ssh_factory
    checksum_probe = checksum_probe or _default_checksum_probe

    stages: dict[str, dict[str, str]] = {
        name: {"status": "not_attempted", "detail": ""} for name in STAGES
    }
    wrapper: Any = None
    try:
        try:
            socket_connect(info.host, info.port, info.timeout)
            stages["port"] = {"status": "PASS", "detail": "reachable"}
        except Exception:
            stages["port"] = {"status": "FAIL", "detail": "port not reachable"}
            return {"status": "FAIL", "profile": "", "stages": stages}

        try:
            wrapper = ssh_factory(info)
            stages["auth"] = {"status": "PASS", "detail": "authenticated"}
        except Exception:
            stages["auth"] = {"status": "FAIL", "detail": "authentication failed"}
            return {"status": "FAIL", "profile": "", "stages": stages}

        try:
            if wrapper is not None and _sftp_available(wrapper):
                stages["sftp"] = {"status": "PASS", "detail": "sftp subsystem available"}
            else:
                stages["sftp"] = {"status": "FAIL", "detail": "sftp subsystem unavailable"}
                return {"status": "FAIL", "profile": "", "stages": stages}
        except Exception:
            stages["sftp"] = {"status": "FAIL", "detail": "sftp subsystem unavailable"}
            return {"status": "FAIL", "profile": "", "stages": stages}

        try:
            available = checksum_probe(wrapper) == 0
        except Exception:
            available = False
        if available:
            stages["checksum"] = {"status": "PASS", "detail": "sha256sum available"}
            return {"status": "PASS", "profile": "", "stages": stages}
        stages["checksum"] = {"status": "FAIL", "detail": "checksum tool not found"}
        return {"status": "FAIL", "profile": "", "stages": stages}
    finally:
        if wrapper is not None:
            try:
                wrapper.close()
            except Exception:
                pass
