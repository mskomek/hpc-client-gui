from __future__ import annotations
from _cli_test_support import (
    json,
    MagicMock,
    patch,
    pytest,
    run_cli,
    SSHConnInfo,
    _isolated_cli_config,  # noqa: F401
)
from _cli_profile_commands import _profile_args

@pytest.mark.unit
@pytest.mark.semantic
def test_saved_dpapi_secret_resolves_without_stdin() -> None:
    from hpc_gui.cli.session import build_ssh_conn_info

    profiles = [{"name": "alpha", "host": "cluster.example", "password_dpapi": "token-123", "cli_allowed": True}]
    with patch("hpc_gui.cli.session.load_profiles", return_value=profiles), patch(
        "hpc_gui.cli.session.secret_store.is_available", return_value=True
    ), patch(
        "hpc_gui.cli.session.secret_store.unprotect_secret", return_value="s3cret"
    ) as unprotect:
        info = build_ssh_conn_info(_profile_args())
    unprotect.assert_called_once_with("token-123")
    assert info.password == "s3cret"


@pytest.mark.unit
@pytest.mark.semantic
def test_profile_without_saved_secret_leaves_password_empty() -> None:
    from hpc_gui.cli.session import build_ssh_conn_info

    profiles = [{"name": "alpha", "host": "cluster.example", "cli_allowed": True}]
    with patch("hpc_gui.cli.session.load_profiles", return_value=profiles), patch(
        "hpc_gui.cli.session.secret_store.is_available", return_value=True
    ), patch("hpc_gui.cli.session.secret_store.unprotect_secret") as unprotect:
        info = build_ssh_conn_info(_profile_args())
    unprotect.assert_not_called()
    assert info.password == ""


@pytest.mark.unit
@pytest.mark.semantic
def test_no_saved_password_flag_skips_dpapi_resolution() -> None:
    from hpc_gui.cli.session import build_ssh_conn_info

    profiles = [{"name": "alpha", "host": "cluster.example", "password_dpapi": "token-123", "cli_allowed": True}]
    with patch("hpc_gui.cli.session.load_profiles", return_value=profiles), patch(
        "hpc_gui.cli.session.secret_store.is_available", return_value=True
    ), patch("hpc_gui.cli.session.secret_store.unprotect_secret") as unprotect:
        info = build_ssh_conn_info(_profile_args(no_saved_password=True))
    unprotect.assert_not_called()
    assert info.password == ""


@pytest.mark.unit
@pytest.mark.semantic
def test_dpapi_unavailable_falls_back_to_empty_password() -> None:
    from hpc_gui.cli.session import build_ssh_conn_info

    profiles = [{"name": "alpha", "host": "cluster.example", "password_dpapi": "token-123", "cli_allowed": True}]
    with patch("hpc_gui.cli.session.load_profiles", return_value=profiles), patch(
        "hpc_gui.cli.session.secret_store.is_available", return_value=False
    ), patch("hpc_gui.cli.session.secret_store.unprotect_secret") as unprotect:
        info = build_ssh_conn_info(_profile_args())
    unprotect.assert_not_called()
    assert info.password == ""


@pytest.mark.unit
@pytest.mark.semantic
def test_key_path_profile_skips_dpapi_resolution() -> None:
    from hpc_gui.cli.session import build_ssh_conn_info

    profiles = [
        {
            "name": "alpha",
            "host": "cluster.example",
            "key_path": "/home/bob/id_rsa",
            "password_dpapi": "token-123",
            "cli_allowed": True,
        }
    ]
    with patch("hpc_gui.cli.session.load_profiles", return_value=profiles), patch(
        "hpc_gui.cli.session.secret_store.is_available", return_value=True
    ), patch("hpc_gui.cli.session.secret_store.unprotect_secret") as unprotect:
        info = build_ssh_conn_info(_profile_args())
    unprotect.assert_not_called()
    assert info.password == ""


@pytest.mark.unit
@pytest.mark.semantic
def test_password_stdin_flag_overrides_saved_secret() -> None:
    from io import StringIO

    from hpc_gui.cli.session import build_ssh_conn_info

    profiles = [{"name": "alpha", "host": "cluster.example", "password_dpapi": "token-123", "cli_allowed": True}]
    with patch("hpc_gui.cli.session.load_profiles", return_value=profiles), patch(
        "hpc_gui.cli.session.secret_store.is_available", return_value=True
    ), patch("hpc_gui.cli.session.secret_store.unprotect_secret") as unprotect, patch(
        "hpc_gui.cli.session.sys.stdin", StringIO("from-stdin\n")
    ):
        info = build_ssh_conn_info(_profile_args(password_stdin=True))
    unprotect.assert_not_called()
    assert info.password == "from-stdin"


@pytest.mark.integration
@pytest.mark.semantic
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
            "cli_allowed": True,
        }
    ]
    with patch("hpc_gui.cli.session.load_profiles", return_value=profiles), patch(
        "hpc_gui.cli.session.SSHClientWrapper", RecordingSSH
    ):
        assert run_cli(["--strict-host-key", "--format", "json", "profile", "test", "alpha"]) == 0
    assert captured[0].host_key_policy == "strict"


@pytest.mark.integration
@pytest.mark.semantic
def test_verbose_debug_only_with_flag_and_key_path_redacted(capsys) -> None:
    key_path = r"C:\private_place\id_rsa"
    args_base = ["--format", "json", "--host", "host", "--user", "user", "--key", key_path]
    fake_ssh_client = MagicMock()
    ssh_inst = fake_ssh_client.return_value
    ssh_inst.get_transport.return_value = None
    ssh_inst.open_sftp.return_value = MagicMock()
    ssh_inst.open_sftp.return_value.listdir_attr.return_value = []
    fake_key = MagicMock()

    with patch("hpc_gui.ssh.client.paramiko.SSHClient", fake_ssh_client), patch(
        "hpc_gui.ssh.client.load_private_key_with_certificate", return_value=fake_key
    ):
        assert run_cli([*args_base, "files", "ls", "/"]) == 0
    plain = capsys.readouterr()
    json.loads(plain.out)
    assert "[debug]" not in plain.err
    assert "private_place" not in plain.out + plain.err

    with patch("hpc_gui.ssh.client.paramiko.SSHClient", fake_ssh_client), patch(
        "hpc_gui.ssh.client.load_private_key_with_certificate", return_value=fake_key
    ):
        assert run_cli(["--verbose", *args_base, "files", "ls", "/"]) == 0
    verbose = capsys.readouterr()
    json.loads(verbose.out)
    assert "[debug]" in verbose.err
    assert "[debug]" not in verbose.out
    assert "using configured key" in verbose.err
    assert "private_place" not in verbose.out + verbose.err
