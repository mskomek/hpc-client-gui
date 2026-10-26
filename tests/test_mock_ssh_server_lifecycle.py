"""Resource ownership checks for the disposable SSH/SFTP test server."""

from __future__ import annotations

import time

import pytest

from support.mock_ssh_server import MOCK_PASSWORD, MOCK_USERNAME, MockSSHServer
from hpc_gui.ssh.client import SSHClientWrapper, SSHConnInfo


@pytest.mark.resource
@pytest.mark.concurrency
def test_server_shutdown_closes_and_joins_active_client_handler(tmp_path):
    server = MockSSHServer(tmp_path)
    server.__enter__()
    client = SSHClientWrapper()
    try:
        client.connect(
            SSHConnInfo(
                host="127.0.0.1",
                port=server.port,
                username=MOCK_USERNAME,
                password=MOCK_PASSWORD,
                host_key_policy="accept-new",
                known_hosts_path=str(tmp_path / "known_hosts"),
            )
        )
        deadline = time.monotonic() + 3.0
        while server.active_client_count == 0 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.active_client_count == 1

        started = time.monotonic()
        server.__exit__()

        assert time.monotonic() - started < 3.0
        assert server.active_client_count == 0
    finally:
        client.close()
        server.__exit__()
