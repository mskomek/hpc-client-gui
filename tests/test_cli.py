from __future__ import annotations

import argparse
import hashlib
import json
import socket
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from truba_gui.cli.errors import ExitCode
from truba_gui.cli.main import _run_doctor, run_cli
from truba_gui.cli.session import CLIConnectionError, CLISession
from truba_gui.services.connection_diagnostics import run_connection_diagnostics
from truba_gui.services.files_base import RemoteEntry
from truba_gui.services.files_ssh import SSHFilesBackend
from truba_gui.services.sftp_smoke import STAGES as SMOKE_STAGES
from truba_gui.services.sftp_smoke import run_sftp_smoke
from truba_gui.ssh.client import SSHClientWrapper, SSHConnInfo


def test_exit_code_timeout_value_lock() -> None:
    assert int(ExitCode.TIMEOUT) == 124


def test_version_json(capsys) -> None:
    assert run_cli(["--format", "json", "version"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["name"] == "hpc-client-gui"
    assert payload["version"]


def test_profile_list_does_not_print_secrets(capsys) -> None:
    profiles = [
        {
            "name": "test",
            "host": "cluster.example",
            "username": "user",
            "password": "should-not-print",
            "password_dpapi": "encrypted-secret",
        }
    ]
    with patch("truba_gui.cli.session.load_profiles", return_value=profiles):
        assert run_cli(["--format", "json", "profile", "show", "test"]) == 0
    output = capsys.readouterr().out
    assert "cluster.example" in output
    assert "should-not-print" not in output
    assert "encrypted-secret" not in output


def test_profile_show_missing_exit_one_with_message(capsys) -> None:
    with patch("truba_gui.cli.session.load_profiles", return_value=[]):
        assert run_cli(["profile", "show", "MISSING"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Profile not found: MISSING" in captured.err


def test_profile_show_never_prints_sensitive_field_values(capsys) -> None:
    profiles = [
        {
            "name": "alpha",
            "host": "cluster.example",
            "username": "user",
            "password": "plain-secret",
            "password_dpapi": "dpapi-token",
            "password_enc": "enc-token",
            "password_salt": "salt-value",
            "system": {"slurm": True},
        }
    ]
    with patch("truba_gui.cli.session.load_profiles", return_value=profiles):
        assert run_cli(["--format", "json", "profile", "show", "alpha"]) == 0
    output = capsys.readouterr().out
    for secret in ("plain-secret", "dpapi-token", "enc-token", "salt-value"):
        assert secret not in output


def test_profile_create_round_trips_to_config_path(capsys, tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    with patch("truba_gui.config.storage._config_path", return_value=config):
        assert (
            run_cli(
                [
                    "--format",
                    "json",
                    "profile",
                    "create",
                    "alpha",
                    "--host",
                    "a.example",
                    "--port",
                    "2222",
                    "--user",
                    "bob",
                    "--key",
                    "/home/bob/id_rsa",
                    "--host-key-policy",
                    "strict",
                ]
            )
            == 0
        )
    payload = json.loads(capsys.readouterr().out)
    assert payload["name"] == "alpha"
    assert payload["host"] == "a.example"
    assert payload["port"] == 2222
    record = json.loads(config.read_text(encoding="utf-8"))["profiles"][0]
    assert record["name"] == "alpha"
    assert record["host"] == "a.example"
    assert record["port"] == 2222
    assert record["username"] == "bob"
    assert record["key_path"] == "/home/bob/id_rsa"
    assert record["host_key_policy"] == "strict"


def test_profile_create_empty_name_maps_to_usage_exit_two(capsys) -> None:
    assert run_cli(["profile", "create", ""]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "profile name is required" in captured.err


def test_profile_update_preserves_secrets_and_system_round_trip(capsys, tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    existing = {
        "name": "alpha",
        "host": "old.example",
        "port": 22,
        "username": "bob",
        "key_path": "",
        "host_key_policy": "accept-new",
        "x11_forwarding": True,
        "save_password": True,
        "password_prompt_policy": "when-needed",
        "password": "",
        "password_dpapi": "encrypted-secret-token",
        "password_enc": "enc-token",
        "password_salt": "salt-value",
        "system": {"slurm": True},
    }
    with patch("truba_gui.config.storage._config_path", return_value=config):
        json.dump({"profiles": [existing]}, config.open("w", encoding="utf-8"))
        assert run_cli(["--format", "json", "profile", "update", "alpha", "--host", "new.example"]) == 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["host"] == "new.example"
    for secret in ("encrypted-secret-token", "enc-token", "salt-value"):
        assert secret not in output
    record = json.loads(config.read_text(encoding="utf-8"))["profiles"][0]
    assert record["host"] == "new.example"
    assert record["password_dpapi"] == "encrypted-secret-token"
    assert record["password_enc"] == "enc-token"
    assert record["password_salt"] == "salt-value"
    assert record["password"] == ""
    assert record["save_password"] is True
    assert record["password_prompt_policy"] == "when-needed"
    assert record["system"] == {"slurm": True}
    assert record["x11_forwarding"] is True
    assert record["port"] == 22
    assert record["username"] == "bob"


def test_profile_update_with_no_field_exits_two_no_write(capsys) -> None:
    with patch("truba_gui.cli.main.load_profiles", return_value=[]), patch(
        "truba_gui.cli.main.upsert_profile"
    ) as upsert:
        assert run_cli(["profile", "update", "alpha"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "--host" in captured.err
    assert "at least one field" in captured.err
    upsert.assert_not_called()


def test_profile_update_missing_name_exit_one_no_write(capsys) -> None:
    with patch("truba_gui.cli.session.load_profiles", return_value=[]), patch(
        "truba_gui.cli.main.upsert_profile"
    ) as upsert:
        assert run_cli(["profile", "update", "MISSING", "--host", "new.example"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Profile not found: MISSING" in captured.err
    assert "profile create" in captured.err
    upsert.assert_not_called()


def test_profile_delete_without_yes_exit_two_no_call(capsys) -> None:
    with patch("truba_gui.cli.main.delete_profile") as delete:
        assert run_cli(["profile", "delete", "alpha"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "--yes" in captured.err
    delete.assert_not_called()


def test_profile_delete_missing_name_exit_one_no_write(capsys) -> None:
    with patch("truba_gui.cli.session.load_profiles", return_value=[]), patch(
        "truba_gui.cli.main.delete_profile"
    ) as delete:
        assert run_cli(["profile", "delete", "MISSING", "--yes"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Profile not found: MISSING" in captured.err
    delete.assert_not_called()


def test_profile_delete_yes_calls_delete_profile_and_exits_zero(capsys) -> None:
    with patch("truba_gui.cli.session.load_profiles", return_value=[{"name": "alpha"}]), patch(
        "truba_gui.cli.main.delete_profile"
    ) as delete:
        assert run_cli(["--format", "json", "profile", "delete", "alpha", "--yes"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["operation"] == "delete"
    assert payload["name"] == "alpha"
    assert payload["status"] == "ok"
    delete.assert_called_once_with("alpha")


def test_doctor_environment_json(capsys, tmp_path: Path) -> None:
    with patch("truba_gui.cli.main.app_data_dir", return_value=tmp_path), patch(
        "truba_gui.cli.main.load_profiles", return_value=[]
    ):
        assert run_cli(["--format", "json", "doctor", "environment"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "PASS"
    assert payload["profiles"] == 0


def test_files_ls_uses_shared_cli_session(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            assert path == "/uzak/klasör"
            return [
                type(
                    "Entry",
                    (),
                    {
                        "name": "dosya_ç.txt",
                        "path": "/uzak/klasör/dosya_ç.txt",
                        "is_dir": False,
                        "size": 3,
                        "mtime": 1,
                        "mode": 0o644,
                    },
                )()
            ]

    class FakeSession:
        files = FakeFiles()

        def close(self):
            pass

    with patch("truba_gui.cli.main.CLISession.open", return_value=FakeSession()):
        assert run_cli(["--format", "json", "--host", "host", "files", "ls", "/uzak/klasör"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["name"] == "dosya_ç.txt"


def test_version_success_exit_zero(capsys) -> None:
    assert run_cli(["version"]) == 0
    assert "version:" in capsys.readouterr().out


def test_files_ls_success_exit_zero(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            assert path == "/"
            return []

    class FakeSession:
        files = FakeFiles()

        def close(self):
            pass

    with patch("truba_gui.cli.main.CLISession.open", return_value=FakeSession()):
        assert run_cli(["--host", "host", "files", "ls", "/"]) == 0


def test_files_rm_refusal_exit_two_stderr_retained(capsys) -> None:
    assert run_cli(["--host", "host", "files", "rm", "/data"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Refusing to remove remote data without --yes." in captured.err


def test_unknown_top_level_argument_exit_two_direct_run_cli_parse() -> None:
    with patch("truba_gui.cli.main.CLISession.open") as session_open:
        with pytest.raises(SystemExit) as excinfo:
            run_cli(["definitely-not-a-command"])
        assert excinfo.value.code == 2
        session_open.assert_not_called()


def test_doctor_unsupported_command_handler_usage_exit_two(capsys) -> None:
    args = argparse.Namespace(doctor_command="unsupported", format="text", quiet=False)
    assert _run_doctor(args) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Unsupported doctor command: unsupported" in captured.err


def test_connection_failure_exit_three(capsys) -> None:
    with patch(
        "truba_gui.cli.main.CLISession.open",
        side_effect=CLIConnectionError("host unreachable"),
    ):
        assert run_cli(["--host", "host", "files", "ls", "/"]) == 3
    captured = capsys.readouterr()
    assert "host unreachable" in captured.err


def test_operation_failure_exit_one(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            raise OSError("disk exploded")

    class FakeSession:
        files = FakeFiles()

        def close(self):
            pass

    with patch("truba_gui.cli.main.CLISession.open", return_value=FakeSession()):
        assert run_cli(["--host", "host", "files", "ls", "/"]) == 1
    captured = capsys.readouterr()
    assert "File operation failed" in captured.err
    assert "disk exploded" in captured.err


def test_json_error_parity_on_failed_remote_op(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            raise OSError("disk exploded")

    class FakeSession:
        files = FakeFiles()

        def close(self):
            pass

    with patch("truba_gui.cli.main.CLISession.open", return_value=FakeSession()):
        assert run_cli(["--format", "json", "--host", "host", "files", "ls", "/"]) == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["error"]["message"] == "File operation failed: disk exploded"
    assert payload["error"]["exit_code"] == 1
    assert captured.err == ""


def test_session_timeout_plumbed_into_connection_info() -> None:
    class FakeSSH:
        def __init__(self, info=None, logger=None, **kwargs):
            self.info = info
            self.logger = logger
            self.sftp = True

        def connect(self):
            pass

        def close(self):
            pass

    args = argparse.Namespace(
        profile="",
        host="cluster.example",
        port=None,
        username="user",
        key_path="",
        strict_host_key=False,
        password_stdin=False,
        timeout=12.5,
        verbose=False,
    )
    with patch("truba_gui.cli.session.SSHClientWrapper", FakeSSH):
        session = CLISession.open(args)
    assert session.ssh.info.timeout == 12.5
    assert session.ssh.logger is None


def test_profile_key_path_flows_into_connection_info() -> None:
    captured: list[SSHConnInfo] = []

    class RecordingSSH:
        def __init__(self, info=None, logger=None, **kwargs):
            self.info = info
            captured.append(info)
            self.sftp = True

        def connect(self):
            pass

        def close(self):
            pass

    profiles = [
        {
            "name": "alpha",
            "host": "cluster.example",
            "port": 22,
            "username": "user",
            "key_path": "/home/bob/id_rsa",
        }
    ]
    args = argparse.Namespace(
        profile="alpha",
        host="",
        port=None,
        username="",
        key_path="",
        strict_host_key=False,
        password_stdin=False,
        timeout=None,
        verbose=False,
    )
    with patch("truba_gui.cli.session.load_profiles", return_value=profiles), patch(
        "truba_gui.cli.session.SSHClientWrapper", RecordingSSH
    ):
        session = CLISession.open(args)
    assert captured[0].key_path == "/home/bob/id_rsa"
    assert captured[0].host_key_policy == "accept-new"
    session.close()


def test_strict_host_key_flag_overrides_profile_accept_new_default() -> None:
    captured: list[SSHConnInfo] = []

    class RecordingSSH:
        def __init__(self, info=None, logger=None, **kwargs):
            self.info = info
            captured.append(info)
            self.sftp = True

        def connect(self):
            pass

        def close(self):
            pass

    profiles = [
        {
            "name": "alpha",
            "host": "cluster.example",
            "port": 22,
            "username": "user",
            "key_path": "",
            "host_key_policy": "accept-new",
        }
    ]
    with patch("truba_gui.cli.session.load_profiles", return_value=profiles), patch(
        "truba_gui.cli.session.SSHClientWrapper", RecordingSSH
    ):
        assert run_cli(["--strict-host-key", "--format", "json", "profile", "test", "alpha"]) == 0
    assert captured[0].host_key_policy == "strict"


def test_verbose_debug_only_with_flag_and_key_path_redacted(capsys) -> None:
    key_path = r"C:\private_place\id_rsa"
    args_base = ["--format", "json", "--host", "host", "--user", "user", "--key", key_path]
    fake_paramiko = MagicMock()
    ssh_inst = fake_paramiko.SSHClient.return_value
    ssh_inst.get_transport.return_value = None
    ssh_inst.open_sftp.return_value = MagicMock()
    ssh_inst.open_sftp.return_value.listdir_attr.return_value = []

    with patch("truba_gui.ssh.client.paramiko", fake_paramiko):
        assert run_cli([*args_base, "files", "ls", "/"]) == 0
    plain = capsys.readouterr()
    json.loads(plain.out)
    assert "[debug]" not in plain.err
    assert "private_place" not in plain.out + plain.err

    with patch("truba_gui.ssh.client.paramiko", fake_paramiko):
        assert run_cli(["--verbose", *args_base, "files", "ls", "/"]) == 0
    verbose = capsys.readouterr()
    json.loads(verbose.out)
    assert "[debug]" in verbose.err
    assert "[debug]" not in verbose.out
    assert "using key" in verbose.err
    assert "private_place" not in verbose.out + verbose.err


def test_files_stat_metadata_parity_with_ls(capsys) -> None:
    attr = SimpleNamespace(filename="data.bin", st_mode=0o100644, st_size=42, st_mtime=987654321)
    fake_sftp = SimpleNamespace(
        listdir_attr=lambda path: [attr],
        stat=lambda path: SimpleNamespace(st_mode=0o100644, st_size=42, st_mtime=987654321),
    )
    fake_ssh = SimpleNamespace(sftp=fake_sftp, supports_transfer_sftp_channels=lambda: False)
    backend = SSHFilesBackend(fake_ssh)

    class FakeSession:
        files = backend

        def close(self):
            pass

    with patch("truba_gui.cli.main.CLISession.open", return_value=FakeSession()):
        assert run_cli(["--format", "json", "--host", "host", "files", "ls", "/data"]) == 0
        ls_payload = json.loads(capsys.readouterr().out)
        assert run_cli(["--format", "json", "--host", "host", "files", "stat", "/data/data.bin"]) == 0
        stat_payload = json.loads(capsys.readouterr().out)
    assert set(stat_payload) == {"name", "path", "type", "size", "mtime", "mode"}
    assert stat_payload["name"] == "data.bin"
    assert stat_payload["path"] == "/data/data.bin"
    for key in ("type", "size", "mtime", "mode"):
        assert stat_payload[key] == ls_payload[0][key]


def test_files_empty_directory_exit_zero(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            return []

    class FakeSession:
        files = FakeFiles()

        def close(self):
            pass

    with patch("truba_gui.cli.main.CLISession.open", return_value=FakeSession()):
        assert run_cli(["--format", "json", "--host", "host", "files", "ls", "/"]) == 0
    assert json.loads(capsys.readouterr().out) == []


def test_files_not_found_exit_one_distinct_message(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            raise FileNotFoundError(f"{path} does not exist")

    class FakeSession:
        files = FakeFiles()

        def close(self):
            pass

    with patch("truba_gui.cli.main.CLISession.open", return_value=FakeSession()):
        assert run_cli(["--host", "host", "files", "ls", "/missing"]) == 1
    captured = capsys.readouterr()
    assert "Not found:" in captured.err
    assert "Permission denied:" not in captured.err


def test_profile_test_success_json_payload_and_session_closed(capsys) -> None:
    closed: list[bool] = []

    class FakeSession:
        profile_name = "alpha"

        def close(self):
            closed.append(True)

    profiles = [{"name": "alpha", "host": "cluster.example", "username": "user"}]
    with patch("truba_gui.cli.session.load_profiles", return_value=profiles), patch(
        "truba_gui.cli.main.CLISession.open", return_value=FakeSession()
    ):
        assert run_cli(["--format", "json", "profile", "test", "alpha"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "PASS"
    assert payload["profile"] == "alpha"
    assert payload["sftp"] is True
    assert closed == [True]


def test_profile_test_connection_failure_exit_three_fail_payload(capsys) -> None:
    with patch(
        "truba_gui.cli.session.load_profiles",
        return_value=[{"name": "alpha", "host": "cluster.example"}],
    ), patch(
        "truba_gui.cli.main.CLISession.open",
        side_effect=CLIConnectionError("host unreachable"),
    ):
        assert run_cli(["--format", "json", "profile", "test", "alpha"]) == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "FAIL"
    assert payload["profile"] == "alpha"
    assert payload["message"] == "host unreachable"


def test_profile_test_connection_failure_text_carries_fail(capsys) -> None:
    with patch(
        "truba_gui.cli.session.load_profiles",
        return_value=[{"name": "alpha", "host": "cluster.example"}],
    ), patch(
        "truba_gui.cli.main.CLISession.open",
        side_effect=CLIConnectionError("host unreachable"),
    ):
        assert run_cli(["profile", "test", "alpha"]) == 3
    captured = capsys.readouterr()
    assert "status: FAIL" in captured.out
    assert "profile: alpha" in captured.out
    assert "host unreachable" in captured.out


def test_profile_test_missing_exit_one_and_opener_not_called(capsys) -> None:
    with patch("truba_gui.cli.session.load_profiles", return_value=[]), patch(
        "truba_gui.cli.main.CLISession.open"
    ) as session_open:
        assert run_cli(["profile", "test", "MISSING"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Profile not found: MISSING" in captured.err
    assert "profile create MISSING" in captured.err
    session_open.assert_not_called()


def test_profile_test_text_mode_matches_json_payload(capsys) -> None:
    class FakeSession:
        profile_name = "alpha"

        def close(self):
            pass

    profiles = [{"name": "alpha", "host": "cluster.example"}]
    with patch("truba_gui.cli.session.load_profiles", return_value=profiles), patch(
        "truba_gui.cli.main.CLISession.open", return_value=FakeSession()
    ):
        assert run_cli(["profile", "test", "alpha"]) == 0
    captured = capsys.readouterr()
    assert "status: PASS" in captured.out
    assert "profile: alpha" in captured.out
    assert "sftp: True" in captured.out


def test_files_access_denied_exit_one_distinct_message(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            raise PermissionError("no access")

    class FakeSession:
        files = FakeFiles()

        def close(self):
            pass

    with patch("truba_gui.cli.main.CLISession.open", return_value=FakeSession()):
        assert run_cli(["--host", "host", "files", "ls", "/"]) == 1
    captured = capsys.readouterr()
    assert "Permission denied:" in captured.err
    assert "Not found:" not in captured.err


def test_files_operation_timeout_exit_124(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            raise TimeoutError("channel stalled")

    class FakeSession:
        files = FakeFiles()

        def close(self):
            pass

    with patch("truba_gui.cli.main.CLISession.open", return_value=FakeSession()):
        assert run_cli(["--host", "host", "files", "ls", "/"]) == 124
    captured = capsys.readouterr()
    assert "Operation timed out" in captured.err


def test_files_ssh_run_124_maps_to_timeout_error() -> None:
    fake_ssh = SimpleNamespace(
        sftp=object(),
        supports_transfer_sftp_channels=lambda: False,
        run=lambda *a, **k: (124, "", ""),
    )
    backend = SSHFilesBackend(fake_ssh)
    with pytest.raises(TimeoutError):
        backend.remove("/x")
    with pytest.raises(TimeoutError):
        backend.sha256("/x")


@pytest.mark.parametrize(
    ("timeout", "expected"),
    [
        (12.5, (12.5, 12.5, 12.5, 12.5)),
        (None, (45, 45, 30, 30)),
    ],
)
def test_connect_plumbs_timeout_into_paramiko_connect_kwargs(timeout, expected) -> None:
    fake_paramiko = MagicMock()
    ssh_inst = fake_paramiko.SSHClient.return_value
    ssh_inst.get_transport.return_value = None
    ssh_inst.open_sftp.return_value = MagicMock()
    info = SSHConnInfo(host="cluster.example", port=22, timeout=timeout)
    with patch("truba_gui.ssh.client.paramiko", fake_paramiko):
        SSHClientWrapper(info=info).connect()
    kwargs = ssh_inst.connect.call_args.kwargs
    assert kwargs["timeout"] == expected[0]
    assert kwargs["banner_timeout"] == expected[1]
    assert kwargs["auth_timeout"] == expected[2]
    assert kwargs["channel_timeout"] == expected[3]


def test_run_defaults_timeout_s_from_info_and_keeps_caller_value() -> None:
    class RecordingChannel:
        def __init__(self) -> None:
            self.settimeouts: list[float] = []

        def settimeout(self, value: float) -> None:
            self.settimeouts.append(value)

        def recv_exit_status(self) -> int:
            return 0

    channels: list[RecordingChannel] = []

    def make_exec(read):
        def exec_command(command: str):
            out_channel = RecordingChannel()
            err_channel = RecordingChannel()
            channels.extend([out_channel, err_channel])
            return (
                MagicMock(),
                SimpleNamespace(channel=out_channel, read=lambda: read()),
                SimpleNamespace(channel=err_channel, read=lambda: b""),
            )

        return exec_command

    wrapper = SSHClientWrapper(info=SSHConnInfo(host="cluster.example", port=22, timeout=7.5))

    wrapper.client = SimpleNamespace(exec_command=make_exec(lambda: b"ok"))
    code, out, err = wrapper.run("echo hi")
    assert code == 0
    assert channels[0].settimeouts == [7.5]
    assert channels[1].settimeouts == [7.5]

    channels.clear()
    code, out, err = wrapper.run("echo hi", timeout_s=3.0)
    assert code == 0
    assert channels[0].settimeouts == [3.0]
    assert channels[1].settimeouts == [3.0]

    channels.clear()
    wrapper.client = SimpleNamespace(exec_command=make_exec(lambda: (_ for _ in ()).throw(socket.timeout("stalled"))))
    code, out, err = wrapper.run("echo hi", timeout_s=2.0)
    assert code == 124
    assert channels[0].settimeouts == [2.0]


def test_files_not_a_directory_exit_one_distinct_message(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            raise NotADirectoryError(f"{path} is not a directory")

    class FakeSession:
        files = FakeFiles()

        def close(self):
            pass

    with patch("truba_gui.cli.main.CLISession.open", return_value=FakeSession()):
        assert run_cli(["--host", "host", "files", "ls", "/missing"]) == 1
    captured = capsys.readouterr()
    assert "Not found:" in captured.err
    assert "Permission denied:" not in captured.err


class FakeFiles:
    """In-memory transfer backend that records calls for if-exists policy tests."""

    def __init__(self, remote=None) -> None:
        self.remote = dict(remote or {})
        self.calls = {"upload": [], "download": [], "remove": [], "exists": [], "sha256": []}

    def exists(self, path):
        self.calls["exists"].append(path)
        return path in self.remote

    def is_dir(self, path):
        return path in self.remote and self.remote[path] is None

    def mkdir(self, path):
        self.remote.setdefault(path, None)

    def remove(self, path, recursive=False):
        self.calls["remove"].append(path)
        self.remote.pop(path, None)

    def listdir_entries(self, path):
        prefix = "" if path in ("", "/") else path.rstrip("/") + "/"
        return [
            type("Entry", (), {"name": key[len(prefix):], "path": key, "is_dir": value is None})()
            for key, value in self.remote.items()
            if key.startswith(prefix) and "/" not in key[len(prefix):]
        ]

    def sha256(self, path):
        self.calls["sha256"].append(path)
        return hashlib.sha256(self.remote.get(path, b"")).hexdigest()

    def upload(self, local_path, remote_path, progress_cb=None):
        self.calls["upload"].append(remote_path)
        self.remote[remote_path] = Path(local_path).read_bytes()

    def download(self, remote_path, local_path, progress_cb=None):
        self.calls["download"].append(remote_path)
        Path(local_path).write_bytes(self.remote[remote_path])


def _run_files(args, files) -> int:
    def fake_session(*_args):
        return SimpleNamespace(files=files, close=lambda: None)

    with patch("truba_gui.cli.main.CLISession.open", side_effect=fake_session):
        return run_cli(args)


def test_files_ls_turkish_directory_json_keeps_type_and_name(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            assert path == "/uzak/klasör"
            return [
                type(
                    "Entry",
                    (),
                    {
                        "name": "klasör_yeni",
                        "path": "/uzak/klasör/klasör_yeni",
                        "is_dir": True,
                        "size": 0,
                        "mtime": 1,
                        "mode": 0o755,
                    },
                )()
            ]

    assert _run_files(["--format", "json", "--host", "host", "files", "ls", "/uzak/klasör"], FakeFiles()) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["type"] == "directory"
    assert payload[0]["name"] == "klasör_yeni"
    assert payload[0]["path"] == "/uzak/klasör/klasör_yeni"


def test_files_ls_turkish_text_keeps_name_and_type_keys(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            assert path == "/uzak/klasör"
            return [
                type(
                    "Entry",
                    (),
                    {
                        "name": "dosya_ç.txt",
                        "path": "/uzak/klasör/dosya_ç.txt",
                        "is_dir": False,
                        "size": 3,
                        "mtime": 1,
                        "mode": 0o644,
                    },
                )(),
                type(
                    "Entry",
                    (),
                    {
                        "name": "klasör_yeni",
                        "path": "/uzak/klasör/klasör_yeni",
                        "is_dir": True,
                        "size": 0,
                        "mtime": 1,
                        "mode": 0o755,
                    },
                )(),
            ]

    assert _run_files(["--host", "host", "files", "ls", "/uzak/klasör"], FakeFiles()) == 0
    out = capsys.readouterr().out
    assert "dosya_ç.txt" in out
    assert "klasör_yeni" in out
    assert "'type': 'file'" in out
    assert "'type': 'directory'" in out


def test_files_stat_turkish_json_six_keys_and_name_preserved(capsys) -> None:
    class FakeFiles:
        def stat_entry(self, path):
            assert path == "/uzak/klasör/ş_veri.txt"
            return RemoteEntry(
                name="ş_veri.txt",
                path="/uzak/klasör/ş_veri.txt",
                is_dir=False,
                size=9,
                mtime=5,
                mode=0o644,
            )

    assert _run_files(["--format", "json", "--host", "host", "files", "stat", "/uzak/klasör/ş_veri.txt"], FakeFiles()) == 0
    payload = json.loads(capsys.readouterr().out)
    assert set(payload) == {"name", "path", "type", "size", "mtime", "mode"}
    assert payload["name"] == "ş_veri.txt"
    assert payload["path"] == "/uzak/klasör/ş_veri.txt"
    assert payload["type"] == "file"


def test_files_stat_turkish_text_keeps_name(capsys) -> None:
    class FakeFiles:
        def stat_entry(self, path):
            return RemoteEntry(
                name="ş_veri.txt",
                path="/uzak/klasör/ş_veri.txt",
                is_dir=False,
                size=9,
                mtime=5,
                mode=0o644,
            )

    assert _run_files(["--host", "host", "files", "stat", "/uzak/klasör/ş_veri.txt"], FakeFiles()) == 0
    out = capsys.readouterr().out
    assert "ş_veri.txt" in out
    assert "/uzak/klasör/ş_veri.txt" in out


def test_files_json_not_found_turkish_detail_parity(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            raise FileNotFoundError("bulunamadı")

    assert _run_files(["--format", "json", "--host", "host", "files", "ls", "/eksik"], FakeFiles()) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["message"].startswith("Not found: ")
    assert "bulunamadı" in payload["error"]["message"]
    assert payload["error"]["exit_code"] == 1


def test_files_json_permission_denied_parity(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            raise PermissionError("erişim engellendi")

    assert _run_files(["--format", "json", "--host", "host", "files", "ls", "/kilitli"], FakeFiles()) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["message"].startswith("Permission denied: ")
    assert "erişim engellendi" in payload["error"]["message"]
    assert payload["error"]["exit_code"] == 1


def test_files_json_not_a_directory_parity(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            raise NotADirectoryError(f"{path} bir dizin değil")

    assert _run_files(["--format", "json", "--host", "host", "files", "ls", "/dosya_ç.txt"], FakeFiles()) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["message"].startswith("Not found: ")
    assert "dosya_ç.txt" in payload["error"]["message"]
    assert payload["error"]["exit_code"] == 1


def test_files_json_timeout_parity(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            raise TimeoutError("işlem zaman aşımı")

    assert _run_files(["--format", "json", "--host", "host", "files", "ls", "/"], FakeFiles()) == 124
    payload = json.loads(capsys.readouterr().out)
    assert "Operation timed out" in payload["error"]["message"]
    assert payload["error"]["exit_code"] == 124


def test_files_ls_empty_directory_text_prints_nothing(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            return []

    assert _run_files(["--host", "host", "files", "ls", "/boş"], FakeFiles()) == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_upload_skip_existing_remote_is_noop(capsys, tmp_path: Path) -> None:
    source = tmp_path / "data.txt"
    source.write_bytes(b"new")
    files = FakeFiles(remote={"/remote/data.txt": b"old"})
    assert _run_files(["--format", "json", "--host", "host", "files", "upload", "--if-exists", "skip", str(source), "/remote/data.txt"], files) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["policy"] == "skip"
    assert payload["files"] == 0
    assert payload["skipped"] == 1
    assert files.calls["upload"] == []
    assert files.remote["/remote/data.txt"] == b"old"


def test_download_skip_existing_local_is_noop(capsys, tmp_path: Path) -> None:
    target = tmp_path / "data.txt"
    target.write_bytes(b"local")
    files = FakeFiles(remote={"/remote/data.txt": b"remote"})
    assert _run_files(["--format", "json", "--host", "host", "files", "download", "--if-exists", "skip", "/remote/data.txt", str(target)], files) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["policy"] == "skip"
    assert payload["files"] == 0
    assert payload["skipped"] == 1
    assert files.calls["download"] == []
    assert target.read_bytes() == b"local"


def test_upload_rename_uses_unique_destination(capsys, tmp_path: Path) -> None:
    source = tmp_path / "data.txt"
    source.write_bytes(b"new")
    files = FakeFiles(remote={"/remote/data.txt": b"old"})
    assert _run_files(["--format", "json", "--host", "host", "files", "upload", "--if-exists", "rename", str(source), "/remote/data.txt"], files) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["policy"] == "rename"
    assert payload["files"] == 1
    assert payload["renames"] == [{"from": "/remote/data.txt", "to": "/remote/data (1).txt"}]
    assert files.calls["upload"] == ["/remote/data (1).txt"]
    assert files.remote["/remote/data.txt"] == b"old"
    assert files.remote["/remote/data (1).txt"] == b"new"


def test_upload_rename_second_collision_uses_two(capsys, tmp_path: Path) -> None:
    source = tmp_path / "data.txt"
    source.write_bytes(b"new")
    files = FakeFiles(remote={"/remote/data.txt": b"old", "/remote/data (1).txt": b"other"})
    assert _run_files(["--format", "json", "--host", "host", "files", "upload", "--if-exists", "rename", str(source), "/remote/data.txt"], files) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["renames"] == [{"from": "/remote/data.txt", "to": "/remote/data (2).txt"}]
    assert files.calls["upload"] == ["/remote/data (2).txt"]


def test_download_rename_never_overwrites_local(capsys, tmp_path: Path) -> None:
    target = tmp_path / "data.txt"
    target.write_bytes(b"local")
    files = FakeFiles(remote={"/remote/data.txt": b"remote"})
    assert _run_files(["--format", "json", "--host", "host", "files", "download", "--if-exists", "rename", "/remote/data.txt", str(target)], files) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["renames"] == [{"from": str(target), "to": str(tmp_path / "data (1).txt")}]
    assert target.read_bytes() == b"local"
    assert (tmp_path / "data (1).txt").read_bytes() == b"remote"
    assert files.calls["download"] == ["/remote/data.txt"]


def test_upload_overwrite_removes_then_uploads(capsys, tmp_path: Path) -> None:
    source = tmp_path / "data.txt"
    source.write_bytes(b"new")
    files = FakeFiles(remote={"/remote/data.txt": b"old"})
    assert _run_files(["--format", "json", "--host", "host", "files", "upload", "--if-exists", "overwrite", str(source), "/remote/data.txt"], files) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["policy"] == "overwrite"
    assert payload["files"] == 1
    assert files.calls["remove"] == ["/remote/data.txt"]
    assert files.calls["upload"] == ["/remote/data.txt"]
    assert files.remote["/remote/data.txt"] == b"new"


def test_upload_resume_no_exists_check_single_call(capsys, tmp_path: Path) -> None:
    source = tmp_path / "data.txt"
    source.write_bytes(b"new")
    files = FakeFiles(remote={"/remote/data.txt": b"old"})
    assert _run_files(["--format", "json", "--host", "host", "files", "upload", "--if-exists", "resume", str(source), "/remote/data.txt"], files) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["policy"] == "resume"
    assert files.calls["exists"] == []
    assert files.calls["upload"] == ["/remote/data.txt"]
    assert files.remote["/remote/data.txt"] == b"new"


def test_upload_skip_with_verify_does_not_verify(capsys, tmp_path: Path) -> None:
    source = tmp_path / "data.txt"
    source.write_bytes(b"new")
    files = FakeFiles(remote={"/remote/data.txt": b"old"})
    assert _run_files(["--format", "json", "--host", "host", "files", "upload", "--if-exists", "skip", "--verify", str(source), "/remote/data.txt"], files) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["skipped"] == 1
    assert files.calls["upload"] == []
    assert files.calls["sha256"] == []


def test_upload_rename_verify_checks_effective_destination(capsys, tmp_path: Path) -> None:
    source = tmp_path / "data.txt"
    source.write_bytes(b"payload")
    files = FakeFiles(remote={"/remote/data.txt": b"old"})
    assert _run_files(["--format", "json", "--host", "host", "files", "upload", "--if-exists", "rename", "--verify", str(source), "/remote/data.txt"], files) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["renames"] == [{"from": "/remote/data.txt", "to": "/remote/data (1).txt"}]
    assert files.calls["sha256"] == ["/remote/data (1).txt"]


def test_upload_skip_text_matches_json_noop(capsys, tmp_path: Path) -> None:
    source = tmp_path / "data.txt"
    source.write_bytes(b"new")
    assert _run_files(["--host", "host", "files", "upload", "--if-exists", "skip", str(source), "/remote/data.txt"], FakeFiles(remote={"/remote/data.txt": b"old"})) == 0
    text = capsys.readouterr().out
    assert "operation: upload" in text
    assert "policy: skip" in text
    assert "files: 0" in text
    assert "skipped: 1" in text
    assert "verified: False" in text


def test_upload_default_if_exists_is_overwrite(capsys, tmp_path: Path) -> None:
    source = tmp_path / "data.txt"
    source.write_bytes(b"new")
    files = FakeFiles(remote={"/remote/data.txt": b"old"})
    assert _run_files(["--format", "json", "--host", "host", "files", "upload", str(source), "/remote/data.txt"], files) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["policy"] == "overwrite"
    assert files.calls["remove"] == ["/remote/data.txt"]
    assert files.calls["upload"] == ["/remote/data.txt"]


def test_upload_recursive_skip_applies_per_file(capsys, tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "a.txt").write_bytes(b"a")
    (src_dir / "b.txt").write_bytes(b"b")
    files = FakeFiles(remote={"/remote/src/a.txt": b"old-a"})
    assert _run_files(["--format", "json", "--host", "host", "files", "upload", "--recursive", "--if-exists", "skip", str(src_dir), "/remote"], files) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["files"] == 1
    assert payload["skipped"] == 1
    assert sorted(files.calls["upload"]) == ["/remote/src/b.txt"]


def _diag_fixture(statuses: dict[str, str]) -> dict:
    return {
        "status": "PASS" if all(value == "PASS" for value in statuses.values()) else "FAIL",
        "profile": "",
        "stages": {
            name: {"status": status, "detail": "detail"}
            for name, status in statuses.items()
        },
    }


def test_diagnostics_socket_fail_marks_later_stages_not_attempted() -> None:
    info = SSHConnInfo(host="cluster.example", port=22)
    payload = run_connection_diagnostics(
        info,
        socket_connect=lambda *_args: (_ for _ in ()).throw(OSError("connection refused")),
        ssh_factory=lambda _info: (_ for _ in ()).throw(AssertionError("unused")),
        checksum_probe=lambda _wrapper: 0,
    )
    assert payload["status"] == "FAIL"
    assert payload["stages"]["port"] == {"status": "FAIL", "detail": "port not reachable"}
    for name in ("auth", "sftp", "checksum"):
        assert payload["stages"][name]["status"] == "not_attempted"
        assert "connection refused" not in payload["stages"][name]["detail"]


def test_diagnostics_auth_fail_after_port_pass() -> None:
    info = SSHConnInfo(host="cluster.example", port=22)
    payload = run_connection_diagnostics(
        info,
        socket_connect=lambda *_args: True,
        ssh_factory=lambda _info: (_ for _ in ()).throw(RuntimeError("bad credentials")),
        checksum_probe=lambda _wrapper: 0,
    )
    assert payload["stages"]["port"]["status"] == "PASS"
    assert payload["stages"]["auth"] == {"status": "FAIL", "detail": "authentication failed"}
    assert payload["stages"]["sftp"]["status"] == "not_attempted"
    assert payload["stages"]["checksum"]["status"] == "not_attempted"
    assert payload["status"] == "FAIL"


def test_diagnostics_sftp_probe_fail_after_auth_pass() -> None:
    class Wrapper:
        def supports_transfer_sftp_channels(self):
            raise OSError("sftp channel broken")

        def close(self):
            pass

    info = SSHConnInfo(host="cluster.example", port=22)
    payload = run_connection_diagnostics(
        info,
        socket_connect=lambda *_args: True,
        ssh_factory=lambda _info: Wrapper(),
        checksum_probe=lambda _wrapper: 0,
    )
    assert payload["stages"]["port"]["status"] == "PASS"
    assert payload["stages"]["auth"]["status"] == "PASS"
    assert payload["stages"]["sftp"] == {"status": "FAIL", "detail": "sftp subsystem unavailable"}
    assert payload["stages"]["checksum"]["status"] == "not_attempted"
    assert payload["status"] == "FAIL"


def test_diagnostics_checksum_nonzero_exit_marks_checksum_fail() -> None:
    class Wrapper:
        def supports_transfer_sftp_channels(self):
            return True

        def close(self):
            pass

    info = SSHConnInfo(host="cluster.example", port=22)
    payload = run_connection_diagnostics(
        info,
        socket_connect=lambda *_args: True,
        ssh_factory=lambda _info: Wrapper(),
        checksum_probe=lambda _wrapper: 1,
    )
    for name in ("port", "auth", "sftp"):
        assert payload["stages"][name]["status"] == "PASS"
    assert payload["stages"]["checksum"]["status"] == "FAIL"
    assert payload["stages"]["checksum"]["detail"] == "checksum tool not found"
    assert payload["status"] == "FAIL"


def test_diagnostics_all_stages_pass_and_wrapper_closed() -> None:
    closed: list[bool] = []

    class Wrapper:
        def supports_transfer_sftp_channels(self):
            return True

        def close(self):
            closed.append(True)

    info = SSHConnInfo(host="cluster.example", port=22)
    payload = run_connection_diagnostics(
        info,
        socket_connect=lambda *_args: True,
        ssh_factory=lambda _info: Wrapper(),
        checksum_probe=lambda _wrapper: 0,
    )
    assert payload["status"] == "PASS"
    assert payload["stages"]["port"] == {"status": "PASS", "detail": "reachable"}
    assert payload["stages"]["auth"] == {"status": "PASS", "detail": "authenticated"}
    assert payload["stages"]["sftp"] == {"status": "PASS", "detail": "sftp subsystem available"}
    assert payload["stages"]["checksum"] == {"status": "PASS", "detail": "sha256sum available"}
    assert closed == [True]


def test_doctor_connection_all_pass_exit_zero_json_four_stages(capsys) -> None:
    fixture = _diag_fixture({"port": "PASS", "auth": "PASS", "sftp": "PASS", "checksum": "PASS"})
    with patch("truba_gui.cli.main.run_connection_diagnostics", return_value=fixture):
        assert run_cli(["--format", "json", "--host", "host", "doctor", "connection"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "PASS"
    assert set(payload["stages"]) == {"port", "auth", "sftp", "checksum"}


def test_doctor_connection_any_fail_exit_three_json_four_stages(capsys) -> None:
    fixture = _diag_fixture(
        {"port": "PASS", "auth": "FAIL", "sftp": "not_attempted", "checksum": "not_attempted"}
    )
    with patch("truba_gui.cli.main.run_connection_diagnostics", return_value=fixture):
        assert run_cli(["--format", "json", "--host", "host", "doctor", "connection"]) == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "FAIL"
    assert set(payload["stages"]) == {"port", "auth", "sftp", "checksum"}


def test_doctor_connection_text_exposes_same_stage_names(capsys) -> None:
    fixture = _diag_fixture(
        {"port": "PASS", "auth": "PASS", "sftp": "PASS", "checksum": "FAIL"}
    )
    with patch("truba_gui.cli.main.run_connection_diagnostics", return_value=fixture):
        assert run_cli(["--host", "host", "doctor", "connection"]) == 3
    out = capsys.readouterr().out
    assert "status: FAIL" in out
    assert "stages:" in out
    for name in ("port", "auth", "sftp", "checksum"):
        assert f'"{name}"' in out


def test_doctor_connection_never_leaks_raw_exception_detail(capsys) -> None:
    secret = "TOP-SECRET-CREDENTIAL-9f4a"

    def bad_factory(_info):
        raise RuntimeError(f"auth rejected: {secret}")

    def wrapped(info):
        return run_connection_diagnostics(
            info,
            socket_connect=lambda *_args: True,
            ssh_factory=bad_factory,
            checksum_probe=lambda _wrapper: 0,
        )

    with patch("truba_gui.cli.main.run_connection_diagnostics", wrapped):
        assert run_cli(["--host", "host", "doctor", "connection"]) == 3
    captured = capsys.readouterr()
    assert secret not in captured.out + captured.err
    assert "authentication failed" in captured.out
    assert "TOP-SECRET" not in captured.out + captured.err


class _MkdirFailFiles(FakeFiles):
    def mkdir(self, path):
        raise OSError("mkdir denied")


class _UploadFailFiles(FakeFiles):
    def upload(self, local_path, remote_path, progress_cb=None):
        raise OSError("upload denied")


class _ListOmitFiles(FakeFiles):
    def listdir_entries(self, path):
        return []


class _DownloadFailFiles(FakeFiles):
    def download(self, remote_path, local_path, progress_cb=None):
        raise OSError("download denied")


class _DownloadCorruptFiles(FakeFiles):
    def download(self, remote_path, local_path, progress_cb=None):
        Path(local_path).write_bytes(b"corrupted")


def test_smoke_all_stages_pass_fixed_order_and_content_round_trip() -> None:
    files = FakeFiles()
    payload = run_sftp_smoke(files, temp_dir_name=lambda: "smoke_dir")
    assert payload["status"] == "PASS"
    assert payload["temp_dir"] == "smoke_dir"
    assert list(payload["stages"]) == list(SMOKE_STAGES)
    assert set(payload["stages"]) == set(SMOKE_STAGES)
    for name in SMOKE_STAGES:
        assert payload["stages"][name]["status"] == "PASS"
    assert files.remote["smoke_dir/smoke.bin"] == b"truba-sftp-smoke"
    assert files.calls["download"] == ["smoke_dir/smoke.bin"]
    assert files.calls["sha256"] == ["smoke_dir/smoke.bin"]
    assert files.calls["remove"] == ["smoke_dir"]


def test_smoke_mkdir_fail_marks_later_stages_not_attempted() -> None:
    payload = run_sftp_smoke(_MkdirFailFiles(), temp_dir_name=lambda: "smoke_dir")
    assert payload["status"] == "FAIL"
    assert set(payload["stages"]) == set(SMOKE_STAGES)
    assert payload["stages"]["temp_dir"]["status"] == "FAIL"
    for name in ("upload", "list", "download", "checksum"):
        assert payload["stages"][name]["status"] == "not_attempted"
    assert payload["stages"]["cleanup"] == {"status": "not_attempted", "detail": "no temp directory"}
    assert "denied" not in payload["stages"]["temp_dir"]["detail"]


def test_smoke_upload_fail_marks_list_download_not_attempted() -> None:
    payload = run_sftp_smoke(_UploadFailFiles(), temp_dir_name=lambda: "smoke_dir")
    assert payload["status"] == "FAIL"
    assert set(payload["stages"]) == set(SMOKE_STAGES)
    assert payload["stages"]["temp_dir"]["status"] == "PASS"
    assert payload["stages"]["upload"]["status"] == "FAIL"
    for name in ("list", "download", "checksum"):
        assert payload["stages"][name]["status"] == "not_attempted"
    assert payload["stages"]["cleanup"]["status"] == "PASS"
    assert "denied" not in payload["stages"]["upload"]["detail"]


def test_smoke_list_omits_file_marks_download_not_attempted() -> None:
    payload = run_sftp_smoke(_ListOmitFiles(), temp_dir_name=lambda: "smoke_dir")
    assert payload["status"] == "FAIL"
    assert set(payload["stages"]) == set(SMOKE_STAGES)
    for name in ("temp_dir", "upload"):
        assert payload["stages"][name]["status"] == "PASS"
    assert payload["stages"]["list"]["status"] == "FAIL"
    assert payload["stages"]["download"]["status"] == "not_attempted"
    assert payload["stages"]["checksum"]["status"] == "not_attempted"
    assert payload["stages"]["cleanup"]["status"] == "PASS"


@pytest.mark.parametrize(
    "backend_cls",
    [_DownloadFailFiles, _DownloadCorruptFiles],
    ids=["download-raises", "download-wrong-bytes"],
)
def test_smoke_download_fail_preserves_completed_passes(backend_cls) -> None:
    payload = run_sftp_smoke(backend_cls(), temp_dir_name=lambda: "smoke_dir")
    assert payload["status"] == "FAIL"
    assert set(payload["stages"]) == set(SMOKE_STAGES)
    for name in ("temp_dir", "upload", "list"):
        assert payload["stages"][name]["status"] == "PASS"
    assert payload["stages"]["download"]["status"] == "FAIL"
    assert payload["stages"]["checksum"]["status"] == "not_attempted"
    assert payload["stages"]["cleanup"]["status"] == "PASS"


def test_smoke_checksum_mismatch_fails_but_runs_cleanup() -> None:
    class _ChecksumMismatchFiles(FakeFiles):
        def sha256(self, path):
            return hashlib.sha256(b"different").hexdigest()

    payload = run_sftp_smoke(_ChecksumMismatchFiles(), temp_dir_name=lambda: "smoke_dir")
    assert payload["status"] == "FAIL"
    assert payload["stages"]["download"]["status"] == "PASS"
    assert payload["stages"]["checksum"]["status"] == "FAIL"
    assert payload["stages"]["checksum"]["detail"] == "checksum mismatch"
    assert payload["stages"]["cleanup"]["status"] == "PASS"


class _RemoveFailFiles(FakeFiles):
    def remove(self, path, recursive=False):
        raise OSError("remove denied")


@pytest.mark.parametrize(
    ("files", "cleanup_flag", "status", "detail"),
    [
        (FakeFiles(), False, "not_attempted", "skipped"),
        (_RemoveFailFiles(), True, "FAIL", "cleanup failed"),
    ],
)
def test_smoke_cleanup_not_pass_combos(files, cleanup_flag, status, detail) -> None:
    payload = run_sftp_smoke(files, temp_dir_name=lambda: "smoke_dir", cleanup=cleanup_flag)
    assert payload["status"] == "FAIL"
    assert payload["stages"]["cleanup"]["status"] == status
    assert payload["stages"]["cleanup"]["detail"] == detail
    if status == "not_attempted":
        assert files.calls["remove"] == []


def _smoke_fixture(statuses: dict[str, str], temp_dir: str = "/tmp/truba-smoke") -> dict:
    return {
        "status": "PASS" if all(value == "PASS" for value in statuses.values()) else "FAIL",
        "profile": "",
        "temp_dir": temp_dir,
        "stages": {
            name: {"status": status, "detail": "detail"}
            for name, status in statuses.items()
        },
    }


def _smoke_all_pass() -> dict:
    return _smoke_fixture({name: "PASS" for name in SMOKE_STAGES})


_PARTIAL = {"temp_dir": "PASS", "upload": "PASS", "list": "FAIL", "download": "not_attempted", "checksum": "not_attempted", "cleanup": "PASS"}


class _FakeSmokeSession:
    files = object()

    def close(self):
        pass


@pytest.mark.parametrize(
    ("extra_args", "expected_cleanup"),
    [([], True), (["--keep"], False)],
)
def test_doctor_smoke_keep_flag_controls_cleanup(extra_args, expected_cleanup, capsys) -> None:
    with patch("truba_gui.cli.main.run_sftp_smoke", return_value=_smoke_all_pass()) as run_mock, patch(
        "truba_gui.cli.main.CLISession.open", return_value=_FakeSmokeSession()
    ):
        assert run_cli(["--format", "json", "--host", "host", "doctor", "smoke", *extra_args]) == 0
    assert run_mock.call_args.kwargs["cleanup"] is expected_cleanup
    payload = json.loads(capsys.readouterr().out)
    assert payload["cleanup_requested"] is expected_cleanup


@pytest.mark.parametrize(
    ("fixture", "expected_exit"),
    [(_smoke_all_pass(), 0), (_smoke_fixture(_PARTIAL), 3)],
)
def test_doctor_smoke_artifact_written(tmp_path, capsys, fixture, expected_exit) -> None:
    artifact = tmp_path / "smoke.json"
    with patch("truba_gui.cli.main.run_sftp_smoke", return_value=fixture), patch(
        "truba_gui.cli.main.CLISession.open", return_value=_FakeSmokeSession()
    ):
        assert run_cli(
            ["--format", "json", "--host", "host", "doctor", "smoke", "--artifact", str(artifact)]
        ) == expected_exit
    data = json.loads(artifact.read_text(encoding="utf-8"))
    assert data["schema"] == "sftp-smoke/1"
    assert data["status"] == fixture["status"]
    assert list(data["stages"]) == list(SMOKE_STAGES)


def test_doctor_smoke_artifact_write_failure_returns_operation_failed(tmp_path, capsys) -> None:
    with patch("truba_gui.cli.main.run_sftp_smoke", return_value=_smoke_all_pass()), patch(
        "truba_gui.cli.main.CLISession.open", return_value=_FakeSmokeSession()
    ):
        result = run_cli(
            ["--host", "host", "doctor", "smoke", "--artifact", str(tmp_path / "missing" / "out.json")]
        )
    assert result == int(ExitCode.OPERATION_FAILED)
    assert "smoke artifact" in capsys.readouterr().err


def test_doctor_smoke_text_and_json_expose_identical_stage_set(capsys) -> None:
    fixture = _smoke_fixture(_PARTIAL)
    with patch("truba_gui.cli.main.run_sftp_smoke", return_value=fixture), patch(
        "truba_gui.cli.main.CLISession.open", return_value=_FakeSmokeSession()
    ):
        assert run_cli(["--host", "host", "doctor", "smoke"]) == 3
    text_out = capsys.readouterr().out
    with patch("truba_gui.cli.main.run_sftp_smoke", return_value=fixture), patch(
        "truba_gui.cli.main.CLISession.open", return_value=_FakeSmokeSession()
    ):
        assert run_cli(["--format", "json", "--host", "host", "doctor", "smoke"]) == 3
    json_payload = json.loads(capsys.readouterr().out)
    assert list(json_payload["stages"]) == list(SMOKE_STAGES)
    for name in SMOKE_STAGES:
        assert f'"{name}"' in text_out


def test_doctor_smoke_closes_session(capsys) -> None:
    closed: list[bool] = []

    class FakeSession:
        files = object()

        def close(self):
            closed.append(True)

    with patch("truba_gui.cli.main.run_sftp_smoke", return_value=_smoke_all_pass()), patch(
        "truba_gui.cli.main.CLISession.open", return_value=FakeSession()
    ):
        assert run_cli(["--format", "json", "--host", "host", "doctor", "smoke"]) == 0
    assert closed == [True]


def test_doctor_smoke_never_leaks_sensitive_detail(capsys) -> None:
    secret = "TOP-SECRET-CREDENTIAL-9f4a"

    class LeakyUploadFiles(FakeFiles):
        def upload(self, local_path, remote_path, progress_cb=None):
            raise RuntimeError(f"upload denied: {secret}")

    class FakeSession:
        files = LeakyUploadFiles()

        def close(self):
            pass

    with patch("truba_gui.cli.main.CLISession.open", return_value=FakeSession()):
        assert run_cli(["--host", "host", "doctor", "smoke"]) == 3
    captured = capsys.readouterr()
    assert secret not in captured.out + captured.err
    assert "upload failed" in captured.out
    assert "TOP-SECRET" not in captured.out + captured.err


class _FakeJobsSSH:
    """Records every command string and returns a fixed run result."""

    def __init__(self, result):
        self.result = result
        self.commands = []

    def run(self, command, **kwargs):
        self.commands.append(command)
        return self.result


class _FakeJobsSession:
    def __init__(self, ssh):
        self.ssh = ssh

    def close(self):
        pass


def _fake_jobs_session(ssh):
    return _FakeJobsSession(ssh)


def test_jobs_help_lists_all_four_subcommands(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        run_cli(["jobs", "--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    for name in ("list", "status", "accounting", "lssrv"):
        assert name in out


def test_jobs_list_text_uses_default_squeue_template(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, "JOBID STATE\n  123 RUNNING\n", ""))
    with patch("truba_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--host", "host", "--user", "alice", "jobs", "list"]) == 0
    assert fake_ssh.commands == ["squeue -u alice"]
    out = capsys.readouterr().out
    assert "JOBID STATE" in out
    assert "123 RUNNING" in out


def test_jobs_list_json_envelope_matches_stdout(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, "JOBID STATE\n  123 RUNNING\n", ""))
    with patch("truba_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--format", "json", "--host", "host", "--user", "alice", "jobs", "list"]) == 0
    assert fake_ssh.commands == ["squeue -u alice"]
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"result": "JOBID STATE\n  123 RUNNING\n"}


def test_jobs_list_username_falls_back_to_profile(capsys) -> None:
    profiles = [{"name": "alpha", "host": "cluster.example", "username": "profileuser"}]
    fake_ssh = _FakeJobsSSH((0, "JOBID STATE\n", ""))
    with patch("truba_gui.cli.session.load_profiles", return_value=profiles), patch(
        "truba_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)
    ):
        assert run_cli(["--profile", "alpha", "jobs", "list"]) == 0
    assert fake_ssh.commands == ["squeue -u profileuser"]


def test_jobs_status_uses_default_scontrol_template(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, "JobId=123 JobName=test State=RUNNING\n", ""))
    with patch("truba_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--host", "host", "jobs", "status", "123"]) == 0
    assert fake_ssh.commands == ["scontrol show job 123"]
    assert "JobId=123" in capsys.readouterr().out


def test_jobs_status_requires_job_id_argument() -> None:
    with patch("truba_gui.cli.main.CLISession.open") as session_open:
        with pytest.raises(SystemExit) as excinfo:
            run_cli(["--host", "host", "jobs", "status"])
        assert excinfo.value.code == 2
        session_open.assert_not_called()


def test_jobs_list_connection_failure_exit_three(capsys) -> None:
    with patch(
        "truba_gui.cli.main.CLISession.open",
        side_effect=CLIConnectionError("host unreachable"),
    ):
        assert run_cli(["--host", "host", "jobs", "list"]) == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "host unreachable" in captured.err


def test_jobs_status_unexpected_exception_exit_one_jobs_prefix(capsys) -> None:
    class BoomSSH(_FakeJobsSSH):
        def run(self, command, **kwargs):
            raise RuntimeError("scheduler exploded")

    with patch("truba_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(BoomSSH((0, "", "")))):
        assert run_cli(["--host", "host", "jobs", "status", "123"]) == 1
    captured = capsys.readouterr()
    assert "Jobs operation failed" in captured.err
    assert "scheduler exploded" in captured.err


_SACCT_COMMAND = "sacct -u alice --format=JobID,JobName,State,Elapsed,MaxRSS,AllocTRES"
_ACCOUNTING_STDOUT = (
    "JobID     JobName     State    Elapsed     MaxRSS   AllocTRES\n"
    "101       compute.cpu RUNNING  00:10:00        512K c01[1-2]\n"
    "102       solver.gpu  FAILED  00:00:05          8K c07[5-6]\n"
)
_LSSRV_STDOUT = "Login node         CPUs    Load\nnode1                32    0.12\n"


def test_jobs_accounting_text_uses_default_sacct_template(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, _ACCOUNTING_STDOUT, ""))
    with patch("truba_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--host", "host", "--user", "alice", "jobs", "accounting"]) == 0
    assert fake_ssh.commands == [_SACCT_COMMAND]
    out = capsys.readouterr().out
    assert "101       compute.cpu RUNNING" in out
    assert "102       solver.gpu  FAILED" in out


def test_jobs_accounting_json_envelope_matches_stdout(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, _ACCOUNTING_STDOUT, ""))
    with patch("truba_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--format", "json", "--host", "host", "--user", "alice", "jobs", "accounting"]) == 0
    assert fake_ssh.commands == [_SACCT_COMMAND]
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"result": _ACCOUNTING_STDOUT}


def test_jobs_accounting_username_falls_back_to_profile(capsys) -> None:
    profiles = [{"name": "alpha", "host": "cluster.example", "username": "profileuser"}]
    fake_ssh = _FakeJobsSSH((0, "Account line\n", ""))
    with patch("truba_gui.cli.session.load_profiles", return_value=profiles), patch(
        "truba_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)
    ):
        assert run_cli(["--profile", "alpha", "jobs", "accounting"]) == 0
    assert fake_ssh.commands == [
        "sacct -u profileuser --format=JobID,JobName,State,Elapsed,MaxRSS,AllocTRES"
    ]


def test_jobs_accounting_connection_failure_exit_three(capsys) -> None:
    with patch(
        "truba_gui.cli.main.CLISession.open",
        side_effect=CLIConnectionError("host unreachable"),
    ):
        assert run_cli(["--host", "host", "jobs", "accounting"]) == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "host unreachable" in captured.err


def test_jobs_lssrv_text_uses_default_status_template(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, _LSSRV_STDOUT, ""))
    with patch("truba_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--host", "host", "jobs", "lssrv"]) == 0
    assert fake_ssh.commands == ["lssrv"]
    out = capsys.readouterr().out
    assert "node1                32    0.12" in out


def test_jobs_lssrv_json_envelope_matches_stdout(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, _LSSRV_STDOUT, ""))
    with patch("truba_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--format", "json", "--host", "host", "jobs", "lssrv"]) == 0
    assert fake_ssh.commands == ["lssrv"]
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"result": _LSSRV_STDOUT}


def test_jobs_lssrv_connection_failure_exit_three(capsys) -> None:
    with patch(
        "truba_gui.cli.main.CLISession.open",
        side_effect=CLIConnectionError("host unreachable"),
    ):
        assert run_cli(["--host", "host", "jobs", "lssrv"]) == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "host unreachable" in captured.err


def test_jobs_lssrv_nonzero_exit_maps_to_operation_failed(capsys) -> None:
    fake_ssh = _FakeJobsSSH((1, "", "lssrv: command not found"))
    with patch("truba_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--host", "host", "jobs", "lssrv"]) == 1
    captured = capsys.readouterr()
    assert "Jobs operation failed" in captured.err
    assert "lssrv: command not found" in captured.err


def test_jobs_submit_yes_submits_script_and_exits_zero(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, "Submitted batch job 12347\n", ""))
    with patch("truba_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--host", "host", "jobs", "submit", "/home/alice/run.sh", "--yes"]) == 0
    assert fake_ssh.commands == ["cd -- /home/alice && sbatch -- run.sh"]
    assert "Submitted batch job 12347" in capsys.readouterr().out


def test_jobs_submit_without_yes_exits_usage_no_session(capsys) -> None:
    with patch("truba_gui.cli.main.CLISession.open") as session_open:
        assert run_cli(["--host", "host", "jobs", "submit", "/home/alice/run.sh"]) == int(ExitCode.USAGE)
    session_open.assert_not_called()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Refusing to submit a job without --yes." in captured.err


def test_jobs_submit_yes_json_envelope_has_result_key(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, "Submitted batch job 12347\n", ""))
    with patch("truba_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--format", "json", "--host", "host", "jobs", "submit", "/home/alice/run.sh", "--yes"]) == 0
    assert fake_ssh.commands == ["cd -- /home/alice && sbatch -- run.sh"]
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"result": "Submitted batch job 12347\n"}


def test_jobs_cancel_yes_cancels_job_and_exits_zero(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, "scancel: Terminated job 12345\n", ""))
    with patch("truba_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--host", "host", "jobs", "cancel", "12345", "--yes"]) == 0
    assert fake_ssh.commands == ["scancel 12345"]
    assert "scancel: Terminated job 12345" in capsys.readouterr().out


def test_jobs_cancel_without_yes_exits_usage_no_session(capsys) -> None:
    with patch("truba_gui.cli.main.CLISession.open") as session_open:
        assert run_cli(["--host", "host", "jobs", "cancel", "12345"]) == int(ExitCode.USAGE)
    session_open.assert_not_called()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Refusing to cancel a job without --yes." in captured.err


def test_jobs_cancel_unsafe_job_id_exits_usage_no_session(capsys) -> None:
    with patch("truba_gui.cli.main.CLISession.open") as session_open:
        assert run_cli(["--host", "host", "jobs", "cancel", "12345; rm -rf /", "--yes"]) == int(
            ExitCode.USAGE
        )
    session_open.assert_not_called()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Invalid job ID: 12345; rm -rf /" in captured.err


def test_jobs_cancel_array_task_id_accepted(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, "scancel: Terminated job 12345_3\n", ""))
    with patch("truba_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--host", "host", "jobs", "cancel", "12345_3", "--yes"]) == 0
    assert fake_ssh.commands == ["scancel 12345_3"]
    assert "scancel: Terminated job 12345_3" in capsys.readouterr().out


def test_jobs_cancel_yes_json_envelope_has_result_key(capsys) -> None:
    fake_ssh = _FakeJobsSSH((0, "scancel: Terminated job 12345\n", ""))
    with patch("truba_gui.cli.main.CLISession.open", return_value=_fake_jobs_session(fake_ssh)):
        assert run_cli(["--format", "json", "--host", "host", "jobs", "cancel", "12345", "--yes"]) == 0
    assert fake_ssh.commands == ["scancel 12345"]
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"result": "scancel: Terminated job 12345"}
