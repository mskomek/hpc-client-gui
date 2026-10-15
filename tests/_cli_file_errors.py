from __future__ import annotations
from _cli_test_support import (
    errno,
    json,
    socket,
    Path,
    SimpleNamespace,
    MagicMock,
    patch,
    pytest,
    ExitCode,
    run_cli,
    SSHClientWrapper,
    SSHConnInfo,
    SSHFilesBackend,
    _isolated_cli_config as _isolated_cli_config,
    _remote_cli_access_enabled as _remote_cli_access_enabled,
)
def _errno_sftp_raiser(exc_factory):
    """SFTP client whose listdir_attr/stat raise a freshly built OSError."""
    return SimpleNamespace(
        listdir_attr=lambda path: (_ for _ in ()).throw(exc_factory()),
        stat=lambda path: (_ for _ in ()).throw(exc_factory()),
    )


def _errno_backend(fake_ssh) -> SSHFilesBackend:
    return SSHFilesBackend(fake_ssh)


def _files_session(backend):
    class FakeSession:
        files = backend

        def close(self):
            pass

    return FakeSession()


@pytest.mark.integration
@pytest.mark.semantic
def test_files_ls_missing_sftp_path_reports_not_found_with_path(capsys) -> None:
    fake_sftp = _errno_sftp_raiser(lambda: OSError(errno.ENOENT, "No such file or directory"))
    backend = _errno_backend(SimpleNamespace(sftp=fake_sftp, supports_transfer_sftp_channels=lambda: False))
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_files_session(backend)):
        assert run_cli(["--host", "host", "files", "ls", "/missing"]) == int(ExitCode.OPERATION_FAILED)
    captured = capsys.readouterr()
    assert "Not found: /missing" in captured.err
    assert "Permission denied:" not in captured.err


@pytest.mark.integration
@pytest.mark.semantic
def test_files_ls_permission_denied_sftp_reports_with_path(capsys) -> None:
    fake_sftp = _errno_sftp_raiser(lambda: OSError(errno.EACCES, "Permission denied"))
    backend = _errno_backend(SimpleNamespace(sftp=fake_sftp, supports_transfer_sftp_channels=lambda: False))
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_files_session(backend)):
        assert run_cli(["--host", "host", "files", "ls", "/locked"]) == int(ExitCode.OPERATION_FAILED)
    captured = capsys.readouterr()
    assert "Permission denied: /locked" in captured.err
    assert "Not found:" not in captured.err


@pytest.mark.integration
@pytest.mark.semantic
def test_files_stat_permission_denied_sftp_reports_with_path(capsys) -> None:
    fake_sftp = _errno_sftp_raiser(lambda: OSError(errno.EACCES, "Permission denied"))
    backend = _errno_backend(SimpleNamespace(sftp=fake_sftp, supports_transfer_sftp_channels=lambda: False))
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_files_session(backend)):
        assert run_cli(["--host", "host", "files", "stat", "/locked/file.txt"]) == int(ExitCode.OPERATION_FAILED)
    captured = capsys.readouterr()
    assert "Permission denied: /locked/file.txt" in captured.err
    assert "Not found:" not in captured.err


@pytest.mark.integration
@pytest.mark.semantic
def test_files_checksum_permission_denied_reports_with_path(capsys) -> None:
    fake_ssh = SimpleNamespace(
        sftp=object(),
        supports_transfer_sftp_channels=lambda: False,
        run=lambda *a, **k: (1, "", "sha256sum: /locked/file.txt: Permission denied"),
    )
    backend = _errno_backend(fake_ssh)
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_files_session(backend)):
        assert run_cli(["--host", "host", "files", "checksum", "/locked/file.txt"]) == int(ExitCode.OPERATION_FAILED)
    captured = capsys.readouterr()
    assert "Permission denied: /locked/file.txt" in captured.err
    assert "Not found:" not in captured.err


@pytest.mark.integration
@pytest.mark.semantic
def test_files_download_permission_denied_reports_with_path(capsys, tmp_path: Path) -> None:
    class TransferSftp:
        def stat(self, path):
            raise OSError(errno.EACCES, "Permission denied")

        def close(self):
            pass

    fake_ssh = SimpleNamespace(
        sftp=_errno_sftp_raiser(lambda: OSError(errno.EACCES, "Permission denied")),
        supports_transfer_sftp_channels=lambda: False,
        open_transfer_sftp=lambda: TransferSftp(),
    )
    backend = _errno_backend(fake_ssh)
    target = tmp_path / "out.txt"
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_files_session(backend)):
        assert run_cli(["--host", "host", "files", "download", "/locked/file.txt", str(target)]) == int(
            ExitCode.OPERATION_FAILED
        )
    captured = capsys.readouterr()
    assert "Permission denied: /locked/file.txt" in captured.err
    assert "Not found:" not in captured.err


@pytest.mark.integration
@pytest.mark.semantic
def test_files_cp_permission_denied_reports_quoted_destination(capsys) -> None:
    fake_ssh = SimpleNamespace(
        sftp=_errno_sftp_raiser(lambda: OSError(errno.EACCES, "Permission denied")),
        supports_transfer_sftp_channels=lambda: False,
        run=lambda *a, **k: (1, "", "cp: cannot create regular file '/no/perm/dst': Permission denied"),
    )
    backend = _errno_backend(fake_ssh)
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_files_session(backend)):
        assert run_cli(["--host", "host", "files", "cp", "/no/perm/src", "/no/perm/dst"]) == int(
            ExitCode.OPERATION_FAILED
        )
    captured = capsys.readouterr()
    assert "Permission denied: /no/perm/dst" in captured.err
    assert "Not found:" not in captured.err


@pytest.mark.integration
@pytest.mark.semantic
def test_files_mv_permission_denied_reports_quoted_source(capsys) -> None:
    fake_ssh = SimpleNamespace(
        sftp=object(),
        supports_transfer_sftp_channels=lambda: False,
        run=lambda *a, **k: (1, "", "mv: cannot stat '/no/perm/path': Permission denied"),
    )
    backend = _errno_backend(fake_ssh)
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_files_session(backend)):
        assert run_cli(["--host", "host", "files", "mv", "/no/perm/path", "/dst"]) == int(ExitCode.OPERATION_FAILED)
    captured = capsys.readouterr()
    assert "Permission denied: /no/perm/path" in captured.err
    assert "Not found:" not in captured.err


@pytest.mark.integration
@pytest.mark.semantic
def test_files_rm_permission_denied_reports_quoted_path(capsys) -> None:
    fake_ssh = SimpleNamespace(
        sftp=object(),
        supports_transfer_sftp_channels=lambda: False,
        run=lambda *a, **k: (1, "", "rm: cannot remove '/no/perm/path': Permission denied"),
    )
    backend = _errno_backend(fake_ssh)
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_files_session(backend)):
        assert run_cli(["--host", "host", "files", "rm", "/no/perm/path", "--yes"]) == int(ExitCode.OPERATION_FAILED)
    captured = capsys.readouterr()
    assert "Permission denied: /no/perm/path" in captured.err
    assert "Not found:" not in captured.err


@pytest.mark.integration
@pytest.mark.semantic
def test_files_rm_missing_reports_not_found_with_path(capsys) -> None:
    fake_ssh = SimpleNamespace(
        sftp=object(),
        supports_transfer_sftp_channels=lambda: False,
        run=lambda *a, **k: (1, "", "rm: cannot remove '/missing/path': No such file or directory"),
    )
    backend = _errno_backend(fake_ssh)
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_files_session(backend)):
        assert run_cli(["--host", "host", "files", "rm", "/missing/path", "--yes"]) == int(ExitCode.OPERATION_FAILED)
    captured = capsys.readouterr()
    assert "Not found: /missing/path" in captured.err
    assert "Permission denied:" not in captured.err


@pytest.mark.integration
@pytest.mark.semantic
def test_files_ls_existing_empty_directory_returns_empty_list(capsys) -> None:
    fake_sftp = SimpleNamespace(listdir_attr=lambda path: [])
    backend = _errno_backend(SimpleNamespace(sftp=fake_sftp, supports_transfer_sftp_channels=lambda: False))
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_files_session(backend)):
        assert run_cli(["--format", "json", "--host", "host", "files", "ls", "/empty"]) == int(ExitCode.SUCCESS)
    assert json.loads(capsys.readouterr().out) == []


@pytest.mark.integration
@pytest.mark.semantic
def test_files_mkdir_shell_failure_stays_generic(capsys) -> None:
    fake_ssh = SimpleNamespace(
        sftp=object(),
        supports_transfer_sftp_channels=lambda: False,
        run=lambda *a, **k: (1, "", "mkdir: cannot create directory '/locked': Permission denied"),
    )
    backend = _errno_backend(fake_ssh)
    with patch("hpc_gui.cli.main.CLISession.open", return_value=_files_session(backend)):
        assert run_cli(["--host", "host", "files", "mkdir", "/locked"]) == int(ExitCode.OPERATION_FAILED)
    captured = capsys.readouterr()
    assert "File operation failed" in captured.err
    assert "Permission denied:" not in captured.err
    assert "Not found:" not in captured.err


@pytest.mark.unit
@pytest.mark.semantic
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
    with patch("hpc_gui.ssh.client.paramiko", fake_paramiko):
        SSHClientWrapper(info=info).connect()
    kwargs = ssh_inst.connect.call_args.kwargs
    assert kwargs["timeout"] == expected[0]
    assert kwargs["banner_timeout"] == expected[1]
    assert kwargs["auth_timeout"] == expected[2]
    assert kwargs["channel_timeout"] == expected[3]


@pytest.mark.unit
@pytest.mark.semantic
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


@pytest.mark.unit
@pytest.mark.semantic
def test_files_not_a_directory_exit_one_distinct_message(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            raise NotADirectoryError(f"{path} is not a directory")

    class FakeSession:
        files = FakeFiles()

        def close(self):
            pass

    with patch("hpc_gui.cli.main.CLISession.open", return_value=FakeSession()):
        assert run_cli(["--host", "host", "files", "ls", "/missing"]) == 1
    captured = capsys.readouterr()
    assert "Not found:" in captured.err
    assert "Permission denied:" not in captured.err
