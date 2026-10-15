from __future__ import annotations
from _cli_test_support import (
    json,
    SimpleNamespace,
    patch,
    pytest,
    run_cli,
    CLIConnectionError,
    SSHFilesBackend,
)
from _cli_transfer_policies import FakeFiles

@pytest.mark.integration
@pytest.mark.semantic
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

    with patch("hpc_gui.cli.main.CLISession.open", return_value=FakeSession()):
        assert run_cli(["--format", "json", "--host", "host", "files", "ls", "/data"]) == 0
        ls_payload = json.loads(capsys.readouterr().out)
        assert run_cli(["--format", "json", "--host", "host", "files", "stat", "/data/data.bin"]) == 0
        stat_payload = json.loads(capsys.readouterr().out)
    assert set(stat_payload) == {"name", "path", "type", "size", "mtime", "mode"}
    assert stat_payload["name"] == "data.bin"
    assert stat_payload["path"] == "/data/data.bin"
    for key in ("type", "size", "mtime", "mode"):
        assert stat_payload[key] == ls_payload[0][key]


@pytest.mark.unit
@pytest.mark.semantic
def test_files_empty_directory_exit_zero(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            return []

    class FakeSession:
        files = FakeFiles()

        def close(self):
            pass

    with patch("hpc_gui.cli.main.CLISession.open", return_value=FakeSession()):
        assert run_cli(["--format", "json", "--host", "host", "files", "ls", "/"]) == 0
    assert json.loads(capsys.readouterr().out) == []


@pytest.mark.unit
@pytest.mark.semantic
def test_files_not_found_exit_one_distinct_message(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            raise FileNotFoundError(f"{path} does not exist")

    class FakeSession:
        files = FakeFiles()

        def close(self):
            pass

    with patch("hpc_gui.cli.main.CLISession.open", return_value=FakeSession()):
        assert run_cli(["--host", "host", "files", "ls", "/missing"]) == 1
    captured = capsys.readouterr()
    assert "Not found:" in captured.err
    assert "Permission denied:" not in captured.err


@pytest.mark.contract
@pytest.mark.semantic
def test_profile_test_success_json_payload_and_session_closed(capsys) -> None:
    closed: list[bool] = []

    class FakeSession:
        profile_name = "alpha"

        def close(self):
            closed.append(True)

    profiles = [{"name": "alpha", "host": "cluster.example", "username": "user"}]
    with patch("hpc_gui.cli.session.load_profiles", return_value=profiles), patch(
        "hpc_gui.cli.main.CLISession.open", return_value=FakeSession()
    ):
        assert run_cli(["--format", "json", "profile", "test", "alpha"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "PASS"
    assert payload["profile"] == "alpha"
    assert payload["sftp"] is True
    assert closed == [True]


@pytest.mark.contract
@pytest.mark.semantic
def test_profile_test_connection_failure_exit_three_fail_payload(capsys) -> None:
    with patch(
        "hpc_gui.cli.session.load_profiles",
        return_value=[{"name": "alpha", "host": "cluster.example"}],
    ), patch(
        "hpc_gui.cli.main.CLISession.open",
        side_effect=CLIConnectionError("host unreachable"),
    ):
        assert run_cli(["--format", "json", "profile", "test", "alpha"]) == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "FAIL"
    assert payload["profile"] == "alpha"
    assert payload["message"] == "host unreachable"


@pytest.mark.contract
@pytest.mark.semantic
def test_profile_test_connection_failure_text_carries_fail(capsys) -> None:
    with patch(
        "hpc_gui.cli.session.load_profiles",
        return_value=[{"name": "alpha", "host": "cluster.example"}],
    ), patch(
        "hpc_gui.cli.main.CLISession.open",
        side_effect=CLIConnectionError("host unreachable"),
    ):
        assert run_cli(["profile", "test", "alpha"]) == 3
    captured = capsys.readouterr()
    assert "status: FAIL" in captured.out
    assert "profile: alpha" in captured.out
    assert "host unreachable" in captured.out


@pytest.mark.unit
@pytest.mark.semantic
def test_profile_test_missing_exit_one_and_opener_not_called(capsys) -> None:
    with patch("hpc_gui.cli.session.load_profiles", return_value=[]), patch(
        "hpc_gui.cli.main.CLISession.open"
    ) as session_open:
        assert run_cli(["profile", "test", "MISSING"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Profile not found: MISSING" in captured.err
    assert "profile create MISSING" in captured.err
    session_open.assert_not_called()


@pytest.mark.contract
@pytest.mark.semantic
def test_profile_test_text_mode_matches_json_payload(capsys) -> None:
    class FakeSession:
        profile_name = "alpha"

        def close(self):
            pass

    profiles = [{"name": "alpha", "host": "cluster.example", "cli_allowed": True}]
    with patch("hpc_gui.cli.session.load_profiles", return_value=profiles), patch(
        "hpc_gui.cli.main.CLISession.open", return_value=FakeSession()
    ):
        assert run_cli(["profile", "test", "alpha"]) == 0
    captured = capsys.readouterr()
    assert "status: PASS" in captured.out
    assert "profile: alpha" in captured.out
    assert "sftp: True" in captured.out


@pytest.mark.unit
@pytest.mark.semantic
def test_files_access_denied_exit_one_distinct_message(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            raise PermissionError("no access")

    class FakeSession:
        files = FakeFiles()

        def close(self):
            pass

    with patch("hpc_gui.cli.main.CLISession.open", return_value=FakeSession()):
        assert run_cli(["--host", "host", "files", "ls", "/"]) == 1
    captured = capsys.readouterr()
    assert "Permission denied:" in captured.err
    assert "Not found:" not in captured.err


@pytest.mark.unit
@pytest.mark.semantic
def test_files_operation_timeout_exit_124(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            raise TimeoutError("channel stalled")

    class FakeSession:
        files = FakeFiles()

        def close(self):
            pass

    with patch("hpc_gui.cli.main.CLISession.open", return_value=FakeSession()):
        assert run_cli(["--host", "host", "files", "ls", "/"]) == 124
    captured = capsys.readouterr()
    assert "Operation timed out" in captured.err


@pytest.mark.unit
@pytest.mark.semantic
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
