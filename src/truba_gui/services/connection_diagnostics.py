"""Connection diagnostics for the ``doctor connection`` CLI flow."""

from __future__ import annotations

import socket
from dataclasses import replace
from typing import Any, Callable, Optional

from truba_gui.ssh.client import SSHClientWrapper, SSHConnInfo


STAGES = ("dns", "port", "auth", "sftp", "slurm", "checksum")


def _default_dns_resolve(host: str, port: int, timeout: Optional[float]) -> None:
    del timeout
    socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)


def _default_socket_connect(host: str, port: int, timeout: Optional[float]) -> socket.socket:
    return socket.create_connection((host, port), timeout=timeout)


def _default_ssh_factory(info: SSHConnInfo) -> SSHClientWrapper:
    wrapper = SSHClientWrapper(info)
    wrapper.connect()
    return wrapper


def _default_slurm_probe(wrapper: SSHClientWrapper) -> int:
    run = getattr(wrapper, "run", None)
    if not callable(run):
        return 0
    code, _out, _err = run("command -v squeue")
    return code


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
    dns_resolve: Optional[Callable[..., Any]] = None,
    ssh_factory: Optional[Callable[..., Any]] = None,
    slurm_probe: Optional[Callable[..., Any]] = None,
    checksum_probe: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """Run the connection stage matrix without exposing connection details."""
    dns_resolve = dns_resolve or (_default_dns_resolve if socket_connect is None else (lambda *_args: None))
    socket_connect = socket_connect or _default_socket_connect
    ssh_factory = ssh_factory or _default_ssh_factory
    slurm_probe = slurm_probe or _default_slurm_probe
    checksum_probe = checksum_probe or _default_checksum_probe
    stages: dict[str, dict[str, str]] = {
        name: {"status": "not_attempted", "detail": ""} for name in STAGES
    }
    wrapper: Any = None
    connected_socket: Any = None
    try:
        try:
            dns_resolve(info.host, info.port, info.timeout)
            stages["dns"] = {"status": "PASS", "detail": "name resolved"}
        except Exception:
            stages["dns"] = {"status": "FAIL", "detail": "name resolution failed"}
            return {"status": "FAIL", "profile": "", "stages": stages}
        try:
            connected_socket = socket_connect(info.host, info.port, info.timeout)
            stages["port"] = {"status": "PASS", "detail": "reachable"}
        except Exception:
            stages["port"] = {"status": "FAIL", "detail": "port not reachable"}
            return {"status": "FAIL", "profile": "", "stages": stages}
        try:
            wrapper = ssh_factory(replace(info, preconnected_socket=connected_socket))
            connected_socket = None
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
            available = slurm_probe(wrapper) == 0
        except Exception:
            available = False
        if available:
            stages["slurm"] = {"status": "PASS", "detail": "scheduler reachable"}
        else:
            stages["slurm"] = {"status": "FAIL", "detail": "scheduler unavailable"}
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
        elif connected_socket is not None:
            try:
                connected_socket.close()
            except Exception:
                pass
