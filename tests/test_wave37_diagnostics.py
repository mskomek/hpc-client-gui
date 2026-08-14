from __future__ import annotations

from hpc_gui.config import storage
from hpc_gui.services.connection_diagnostics import run_connection_diagnostics
from hpc_gui.ssh.client import SSHConnInfo


def test_diagnostics_includes_dns_and_slurm_stages() -> None:
    class Wrapper:
        def supports_transfer_sftp_channels(self):
            return True

        def close(self):
            pass

    payload = run_connection_diagnostics(
        SSHConnInfo(host="cluster.example", port=22),
        dns_resolve=lambda *_args: None,
        socket_connect=lambda *_args: object(),
        ssh_factory=lambda _info: Wrapper(),
        slurm_probe=lambda _wrapper: 0,
        checksum_probe=lambda _wrapper: 0,
    )
    assert payload["status"] == "PASS"
    assert tuple(payload["stages"]) == ("dns", "port", "auth", "sftp", "slurm", "checksum")


def test_profile_conflict_preference_can_be_set_and_reset(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(storage, "_config_path", lambda: config_path)
    monkeypatch.setattr(storage, "_config_dir", lambda: tmp_path)
    storage.save_config({"profiles": [{"name": "one", "host": "h"}], "settings": {}})
    assert storage.set_profile_conflict_action("one", "overwrite_if_newer") == "overwrite_if_newer"
    assert storage.get_profile_conflict_action("one") == "overwrite_if_newer"
    storage.clear_profile_conflict_action("one")
    assert storage.get_profile_conflict_action("one") is None
