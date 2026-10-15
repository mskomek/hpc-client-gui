from __future__ import annotations
from _cli_test_support import (
    argparse,
    json,
    Path,
    patch,
    pytest,
    ExitCode,
    _run_doctor,
    run_cli,
    CLIConnectionError,
    CLISession,
    SSHConnInfo,
)
from _cli_transfer_policies import FakeFiles

@pytest.mark.contract
def test_exit_code_timeout_value_lock() -> None:
    assert int(ExitCode.TIMEOUT) == 124


@pytest.mark.contract
def test_version_json(capsys) -> None:
    assert run_cli(["--format", "json", "version"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["name"] == "hpc-client-gui"
    assert payload["version"]


@pytest.mark.unit
@pytest.mark.semantic
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
    with patch("hpc_gui.cli.session.load_profiles", return_value=profiles):
        assert run_cli(["--format", "json", "profile", "show", "test"]) == 0
    output = capsys.readouterr().out
    assert "cluster.example" in output
    assert "should-not-print" not in output
    assert "encrypted-secret" not in output


@pytest.mark.unit
@pytest.mark.semantic
def test_profile_show_missing_exit_one_with_message(capsys) -> None:
    with patch("hpc_gui.cli.session.load_profiles", return_value=[]):
        assert run_cli(["profile", "show", "MISSING"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Profile not found: MISSING" in captured.err


@pytest.mark.unit
@pytest.mark.semantic
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
    with patch("hpc_gui.cli.session.load_profiles", return_value=profiles):
        assert run_cli(["--format", "json", "profile", "show", "alpha"]) == 0
    output = capsys.readouterr().out
    for secret in ("plain-secret", "dpapi-token", "enc-token", "salt-value"):
        assert secret not in output


@pytest.mark.integration
@pytest.mark.semantic
def test_profile_create_round_trips_to_config_path(capsys, tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    with patch("hpc_gui.config.storage._config_path", return_value=config):
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


@pytest.mark.unit
@pytest.mark.semantic
def test_profile_create_empty_name_maps_to_usage_exit_two(capsys) -> None:
    assert run_cli(["profile", "create", ""]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "profile name is required" in captured.err


@pytest.mark.integration
@pytest.mark.semantic
@pytest.mark.regression
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
    with patch("hpc_gui.config.storage._config_path", return_value=config):
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


@pytest.mark.unit
@pytest.mark.semantic
def test_profile_update_with_no_field_exits_two_no_write(capsys) -> None:
    with patch("hpc_gui.cli.main.load_profiles", return_value=[]), patch(
        "hpc_gui.cli.main.upsert_profile"
    ) as upsert:
        assert run_cli(["profile", "update", "alpha"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "--host" in captured.err
    assert "at least one field" in captured.err
    upsert.assert_not_called()


@pytest.mark.unit
@pytest.mark.semantic
def test_profile_update_missing_name_exit_one_no_write(capsys) -> None:
    with patch("hpc_gui.cli.session.load_profiles", return_value=[]), patch(
        "hpc_gui.cli.main.upsert_profile"
    ) as upsert:
        assert run_cli(["profile", "update", "MISSING", "--host", "new.example"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Profile not found: MISSING" in captured.err
    assert "profile create" in captured.err
    upsert.assert_not_called()


@pytest.mark.unit
@pytest.mark.semantic
def test_profile_delete_without_yes_exit_two_no_call(capsys) -> None:
    with patch("hpc_gui.cli.main.delete_profile") as delete:
        assert run_cli(["profile", "delete", "alpha"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "--yes" in captured.err
    delete.assert_not_called()


@pytest.mark.unit
@pytest.mark.semantic
def test_profile_delete_missing_name_exit_one_no_write(capsys) -> None:
    with patch("hpc_gui.cli.session.load_profiles", return_value=[]), patch(
        "hpc_gui.cli.main.delete_profile"
    ) as delete:
        assert run_cli(["profile", "delete", "MISSING", "--yes"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Profile not found: MISSING" in captured.err
    delete.assert_not_called()


@pytest.mark.unit
@pytest.mark.semantic
def test_profile_delete_yes_calls_delete_profile_and_exits_zero(capsys) -> None:
    with patch("hpc_gui.cli.session.load_profiles", return_value=[{"name": "alpha"}]), patch(
        "hpc_gui.cli.main.delete_profile"
    ) as delete:
        assert run_cli(["--format", "json", "profile", "delete", "alpha", "--yes"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["operation"] == "delete"
    assert payload["name"] == "alpha"
    assert payload["status"] == "ok"
    delete.assert_called_once_with("alpha")


@pytest.mark.unit
@pytest.mark.semantic
def test_doctor_environment_json(capsys, tmp_path: Path) -> None:
    with patch("hpc_gui.cli.main.app_data_dir", return_value=tmp_path), patch(
        "hpc_gui.cli.main.load_profiles", return_value=[]
    ):
        assert run_cli(["--format", "json", "doctor", "environment"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "PASS"
    assert payload["profiles"] == 0


@pytest.mark.unit
@pytest.mark.semantic
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

    with patch("hpc_gui.cli.main.CLISession.open", return_value=FakeSession()):
        assert run_cli(["--format", "json", "--host", "host", "files", "ls", "/uzak/klasör"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["name"] == "dosya_ç.txt"


@pytest.mark.contract
def test_version_success_exit_zero(capsys) -> None:
    assert run_cli(["version"]) == 0
    assert "version:" in capsys.readouterr().out


@pytest.mark.unit
def test_files_ls_success_exit_zero(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            assert path == "/"
            return []

    class FakeSession:
        files = FakeFiles()

        def close(self):
            pass

    with patch("hpc_gui.cli.main.CLISession.open", return_value=FakeSession()):
        assert run_cli(["--host", "host", "files", "ls", "/"]) == 0


@pytest.mark.unit
@pytest.mark.semantic
def test_files_rm_refusal_exit_two_stderr_retained(capsys) -> None:
    assert run_cli(["--host", "host", "files", "rm", "/data"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Refusing to remove remote data without --yes." in captured.err


@pytest.mark.unit
@pytest.mark.semantic
def test_unknown_top_level_argument_exit_two_direct_run_cli_parse() -> None:
    with patch("hpc_gui.cli.main.CLISession.open") as session_open:
        with pytest.raises(SystemExit) as excinfo:
            run_cli(["definitely-not-a-command"])
        assert excinfo.value.code == 2
        session_open.assert_not_called()


@pytest.mark.unit
@pytest.mark.semantic
def test_doctor_unsupported_command_handler_usage_exit_two(capsys) -> None:
    args = argparse.Namespace(doctor_command="unsupported", format="text", quiet=False)
    assert _run_doctor(args) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Unsupported doctor command: unsupported" in captured.err


@pytest.mark.unit
@pytest.mark.semantic
def test_connection_failure_exit_three(capsys) -> None:
    with patch(
        "hpc_gui.cli.main.CLISession.open",
        side_effect=CLIConnectionError("host unreachable"),
    ):
        assert run_cli(["--host", "host", "files", "ls", "/"]) == 3
    captured = capsys.readouterr()
    assert "host unreachable" in captured.err


@pytest.mark.unit
@pytest.mark.semantic
def test_operation_failure_exit_one(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            raise OSError("disk exploded")

    class FakeSession:
        files = FakeFiles()

        def close(self):
            pass

    with patch("hpc_gui.cli.main.CLISession.open", return_value=FakeSession()):
        assert run_cli(["--host", "host", "files", "ls", "/"]) == 1
    captured = capsys.readouterr()
    assert "File operation failed" in captured.err
    assert "disk exploded" in captured.err


@pytest.mark.contract
@pytest.mark.semantic
def test_json_error_parity_on_failed_remote_op(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            raise OSError("disk exploded")

    class FakeSession:
        files = FakeFiles()

        def close(self):
            pass

    with patch("hpc_gui.cli.main.CLISession.open", return_value=FakeSession()):
        assert run_cli(["--format", "json", "--host", "host", "files", "ls", "/"]) == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["error"]["message"] == "File operation failed: disk exploded"
    assert payload["error"]["exit_code"] == 1
    assert captured.err == ""


@pytest.mark.integration
@pytest.mark.semantic
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
    with patch("hpc_gui.cli.session.SSHClientWrapper", FakeSSH):
        session = CLISession.open(args)
    assert session.ssh.info.timeout == 12.5
    assert session.ssh.logger is None


@pytest.mark.integration
@pytest.mark.semantic
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
            "cli_allowed": True,
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
    with patch("hpc_gui.cli.session.load_profiles", return_value=profiles), patch(
        "hpc_gui.cli.session.SSHClientWrapper", RecordingSSH
    ):
        session = CLISession.open(args)
    assert captured[0].key_path == "/home/bob/id_rsa"
    assert captured[0].host_key_policy == "accept-new"
    session.close()


def _profile_args(**overrides) -> argparse.Namespace:
    base = dict(
        profile="alpha",
        host="",
        port=None,
        username="",
        key_path="",
        strict_host_key=False,
        password_stdin=False,
        no_saved_password=False,
        timeout=None,
        verbose=False,
    )
    base.update(overrides)
    return argparse.Namespace(**base)
