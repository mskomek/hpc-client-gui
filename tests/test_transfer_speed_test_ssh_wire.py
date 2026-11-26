from __future__ import annotations

import paramiko
import pytest

from hpc_gui.services.files_ssh import SSHFilesBackend
from hpc_gui.services.transfer_speed_test import run_transfer_speed_test
from hpc_gui.ssh import client as ssh_client_module
from hpc_gui.ssh.client import SSHClientWrapper, SSHConnInfo
from support.mock_ssh_server import MOCK_PASSWORD, MOCK_USERNAME, MockSSHServer


@pytest.mark.integration
def test_transfer_speed_test_uses_disposable_loopback_ssh_sftp(tmp_path, monkeypatch):
    app_data = tmp_path / "app-data"
    app_data.mkdir()
    monkeypatch.setattr(ssh_client_module, "app_data_dir", lambda: app_data)
    monkeypatch.setattr(paramiko.SSHClient, "load_system_host_keys", lambda _self: None)
    remote_root = tmp_path / "remote"
    (remote_root / "scratch").mkdir(parents=True)

    with MockSSHServer(remote_root, listen_host="127.0.0.1") as server:
        ssh = SSHClientWrapper(
            SSHConnInfo(
                host="127.0.0.1",
                port=server.port,
                username=MOCK_USERNAME,
                password=MOCK_PASSWORD,
                host_key_policy="accept-new",
                host_key_decision=lambda _info: "save",
                timeout=10,
            )
        )
        ssh.connect()
        try:
            files = SSHFilesBackend(ssh)
            result = run_transfer_speed_test(files, remote_dir="/scratch", size_mib=1)
            assert result["size_mib"] == 1
            assert result["upload_mib_s"] > 0
            assert result["download_mib_s"] > 0
            assert list((remote_root / "scratch").iterdir()) == []
        finally:
            ssh.close()
