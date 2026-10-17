from __future__ import annotations
from _cli_test_support import (
    argparse,
    json,
    Path,
    patch,
    pytest,
    ExitCode,
    run_cli,
    CLIConnectionError,
    _isolated_cli_config,  # noqa: F401
)
@pytest.mark.integration
@pytest.mark.semantic
def test_cli_settings_round_trip_and_defaults(tmp_path: Path) -> None:
    from hpc_gui.config.storage import (
        get_cli_default_profile,
        get_cli_external_access_enabled,
        set_cli_default_profile,
        set_cli_external_access_enabled,
    )

    config = tmp_path / "config.json"
    with patch("hpc_gui.config._storage_core._config_path", return_value=config):
        assert get_cli_external_access_enabled() is False
        assert get_cli_default_profile() == ""
        assert set_cli_external_access_enabled(True) is True
        assert set_cli_default_profile("  beta  ") == "beta"
        assert get_cli_external_access_enabled() is True
        assert get_cli_default_profile() == "beta"
    record = json.loads(config.read_text(encoding="utf-8"))["settings"]
    assert record["cli_external_access_enabled"] is True
    assert record["cli_default_profile"] == "beta"


def _run_gate_blocked(argv: list[str], capsys) -> int:
    with patch("hpc_gui.cli.main.CLISession.open") as session_open, patch(
        "hpc_gui.cli.main.get_cli_external_access_enabled", return_value=False
    ):
        code = run_cli(argv)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Allow external CLI access to remote commands" in captured.err
    session_open.assert_not_called()
    return code


@pytest.mark.unit
@pytest.mark.semantic
@pytest.mark.parametrize(
    "argv",
    [
        ["--host", "host", "files", "ls", "/"],
        ["--host", "host", "jobs", "list"],
        ["profile", "test", "alpha"],
        ["--host", "host", "doctor", "connection"],
        ["--host", "host", "doctor", "smoke"],
    ],
    ids=["files-ls", "jobs-list", "profile-test", "doctor-connection", "doctor-smoke"],
)
def test_access_gate_off_blocks_remote_commands(capsys, argv) -> None:
    assert _run_gate_blocked(argv, capsys) == int(ExitCode.OPERATION_FAILED)


@pytest.mark.contract
@pytest.mark.semantic
def test_access_gate_off_blocked_command_json(capsys) -> None:
    with patch("hpc_gui.cli.main.CLISession.open") as session_open, patch(
        "hpc_gui.cli.main.get_cli_external_access_enabled", return_value=False
    ):
        assert run_cli(["--format", "json", "--host", "host", "files", "ls", "/"]) == int(
            ExitCode.OPERATION_FAILED
        )
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["exit_code"] == int(ExitCode.OPERATION_FAILED)
    assert "Allow external CLI access to remote commands" in payload["error"]["message"]
    session_open.assert_not_called()


@pytest.mark.unit
@pytest.mark.semantic
def test_access_gate_off_exempt_commands_still_succeed(capsys, tmp_path: Path) -> None:
    profiles = [{"name": "alpha", "host": "cluster.example", "username": "user"}]
    with patch("hpc_gui.cli.session.load_profiles", return_value=profiles), patch(
        "hpc_gui.cli._profile_commands.load_profiles", return_value=profiles
    ), patch(
        "hpc_gui.cli._doctor_commands.load_profiles", return_value=profiles
    ), patch("hpc_gui.cli._doctor_commands.app_data_dir", return_value=tmp_path), patch(
        "hpc_gui.cli.main.get_cli_external_access_enabled", return_value=False
    ):
        assert run_cli(["--format", "json", "version"]) == 0
        assert run_cli(["--format", "json", "commands"]) == 0
        assert run_cli(["--format", "json", "profile", "list"]) == 0
        assert run_cli(["--format", "json", "doctor", "environment"]) == 0
        assert run_cli(["--format", "json", "profile", "show", "alpha"]) == 0
    captured = capsys.readouterr().out
    assert '"name": "alpha"' in captured
    assert '"profiles": 1' in captured


@pytest.mark.unit
@pytest.mark.semantic
def test_access_gate_on_allows_denied_command(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            return []

    class FakeSession:
        files = FakeFiles()

        def close(self):
            pass

    with patch("hpc_gui.cli.main.CLISession.open", return_value=FakeSession()), patch(
        "hpc_gui.cli.main.get_cli_external_access_enabled", return_value=True
    ):
        assert run_cli(["--format", "json", "--host", "host", "files", "ls", "/"]) == 0
    captured = capsys.readouterr()
    assert "Allow external CLI access" not in captured.err
    assert json.loads(captured.out) == []


@pytest.mark.unit
@pytest.mark.semantic
def test_effective_profile_name_falls_back_to_saved_default() -> None:
    from hpc_gui.cli.session import effective_profile_name

    args = argparse.Namespace(profile="")
    with patch("hpc_gui.config.storage.get_cli_default_profile", return_value="default"):
        assert effective_profile_name(args) == "default"


@pytest.mark.unit
@pytest.mark.semantic
def test_effective_profile_name_explicit_overrides_default() -> None:
    from hpc_gui.cli.session import effective_profile_name

    args = argparse.Namespace(profile="explicit")
    with patch("hpc_gui.config.storage.get_cli_default_profile", return_value="default"):
        assert effective_profile_name(args) == "explicit"


def _conn_info_args(**overrides) -> argparse.Namespace:
    base = dict(
        profile="",
        host="",
        port=None,
        username="",
        key_path="",
        strict_host_key=False,
        password_stdin=False,
        no_saved_password=True,
        timeout=None,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


@pytest.mark.unit
@pytest.mark.semantic
def test_build_ssh_conn_info_uses_default_profile_when_no_flag() -> None:
    from hpc_gui.cli.session import build_ssh_conn_info

    profiles = [{"name": "default", "host": "default.example", "username": "du", "cli_allowed": True}]
    with patch("hpc_gui.cli.session.load_profiles", return_value=profiles), patch(
        "hpc_gui.config.storage.get_cli_default_profile", return_value="default"
    ):
        info = build_ssh_conn_info(_conn_info_args())
    assert info.host == "default.example"
    assert info.username == "du"


@pytest.mark.unit
@pytest.mark.semantic
def test_build_ssh_conn_info_explicit_profile_overrides_default() -> None:
    from hpc_gui.cli.session import build_ssh_conn_info

    profiles = [
        {"name": "explicit", "host": "explicit.example", "username": "eu", "cli_allowed": True},
        {"name": "default", "host": "default.example", "username": "du", "cli_allowed": True},
    ]
    with patch("hpc_gui.cli.session.load_profiles", return_value=profiles), patch(
        "hpc_gui.config.storage.get_cli_default_profile", return_value="default"
    ):
        info = build_ssh_conn_info(_conn_info_args(profile="explicit"))
    assert info.host == "explicit.example"
    assert info.username == "eu"


@pytest.mark.unit
@pytest.mark.semantic
def test_build_ssh_conn_info_stale_default_profile_raises() -> None:
    from hpc_gui.cli.session import build_ssh_conn_info

    with patch("hpc_gui.cli.session.load_profiles", return_value=[]), patch(
        "hpc_gui.config.storage.get_cli_default_profile", return_value="ghost"
    ):
        with pytest.raises(CLIConnectionError, match="Profile not found: ghost"):
            build_ssh_conn_info(_conn_info_args())


@pytest.mark.unit
@pytest.mark.semantic
@pytest.mark.parametrize(
    ("saved", "expected"),
    [(120, 120), (999999, 3600), (-5, 0), ("oops", 30), (None, 30)],
)
def test_build_ssh_conn_info_keepalive_from_profile(saved, expected: int) -> None:
    from hpc_gui.cli.session import build_ssh_conn_info

    profile = {"name": "alpha", "host": "cluster.example", "cli_allowed": True}
    if saved is not None:
        profile["keepalive_interval_seconds"] = saved
    profiles = [profile]
    with patch("hpc_gui.cli.session.load_profiles", return_value=profiles):
        info = build_ssh_conn_info(_conn_info_args(profile="alpha"))
    assert info.keepalive_interval_seconds == expected


@pytest.mark.unit
@pytest.mark.semantic
def test_jobs_username_honors_default_profile() -> None:
    from hpc_gui.cli.main import _jobs_username

    args = argparse.Namespace(profile="", username="")
    with patch("hpc_gui.cli._shared.effective_profile_name", return_value="alpha"), patch(
        "hpc_gui.cli._shared.resolve_profile",
        return_value={"name": "alpha", "username": "defaultuser"},
    ):
        assert _jobs_username(args) == "defaultuser"


@pytest.mark.unit
@pytest.mark.semantic
def test_jobs_username_explicit_profile_beats_default() -> None:
    from hpc_gui.cli.main import _jobs_username

    args = argparse.Namespace(profile="explicit", username="")
    with patch("hpc_gui.cli._shared.effective_profile_name", return_value="explicit"), patch(
        "hpc_gui.cli._shared.resolve_profile",
        return_value={"name": "explicit", "username": "explicituser"},
    ):
        assert _jobs_username(args) == "explicituser"


@pytest.mark.contract
@pytest.mark.semantic
def test_commands_json_inventory_matches_parser_and_exit_codes(capsys) -> None:
    assert run_cli(["--format", "json", "commands"]) == 0
    payload = json.loads(capsys.readouterr().out)
    paths = [entry["path"] for entry in payload["commands"]]
    assert "files ls" in paths
    assert "jobs submit" in paths
    assert payload["exit_codes"] == {code.name: int(code.value) for code in ExitCode}


@pytest.mark.contract
@pytest.mark.semantic
def test_unknown_top_level_group_prints_full_help(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        run_cli(["fles"])
    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "usage:" in captured.err
    assert "--format" in captured.err
    assert "Examples:" in captured.err


@pytest.mark.contract
@pytest.mark.semantic
def test_unknown_files_subcommand_prints_full_group_help(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        run_cli(["files", "lss"])
    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "usage:" in captured.err
    assert "ls" in captured.err
    assert "upload" in captured.err


@pytest.mark.contract
@pytest.mark.semantic
def test_root_help_contains_examples_block(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        run_cli(["--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "Examples:" in out
    assert "hpc-client-gui --profile arf files ls /home" in out
