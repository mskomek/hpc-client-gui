"""Network binding guarantees for the reusable mock SSH server."""

from __future__ import annotations

import socket

from support.mock_ssh_server import MockSSHServer


def test_mock_ssh_server_binds_to_explicit_loopback_interface(tmp_path):
    """Explicit bind configuration remains reachable and does not change defaults."""
    with MockSSHServer(tmp_path, listen_host="127.0.0.1") as server:
        assert server.listen_host == "127.0.0.1"
        with socket.create_connection((server.listen_host, server.port), timeout=2):
            pass


def test_mock_ssh_server_defaults_to_loopback(tmp_path):
    with MockSSHServer(tmp_path) as server:
        assert server.listen_host == "127.0.0.1"
        with socket.create_connection((server.listen_host, server.port), timeout=2):
            pass
