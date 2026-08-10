from __future__ import annotations

import sys
from io import StringIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

from truba_gui.cli.main import _normalize_alias_argv, _parser, _run_script, _run_sh, run_cli
from truba_gui.cli.session import CLIConnectionError, CLISession, build_ssh_conn_info


def test_console_entry_parser_exposes_masked_password_prompt() -> None:
    args = _parser().parse_args(["--password-prompt", "version"])
    assert args.password_prompt is True


def test_console_entry_defaults_to_interactive_prompt() -> None:
    with patch("truba_gui.cli.main._run_interactive", return_value=0) as interactive:
        assert run_cli([], default_group="interactive") == 0
    interactive.assert_called_once()


def test_password_prompt_rejects_non_interactive_stdin() -> None:
    args = _parser().parse_args(["--host", "example", "--password-prompt", "version"])
    with patch.object(sys, "stdin", StringIO("")), patch.object(sys, "stderr", StringIO()):
        try:
            build_ssh_conn_info(args)
        except CLIConnectionError as exc:
            assert "interactive terminal" in str(exc)
        else:
            raise AssertionError("non-interactive password prompt was accepted")


def test_root_aliases_normalize_to_canonical_commands() -> None:
    assert _normalize_alias_argv(["--profile", "p", "squeue"]) == [
        "--profile", "p", "jobs", "list"
    ]
    assert _normalize_alias_argv(["put", "local", "/remote"]) == [
        "files", "upload", "local", "/remote"
    ]


def test_ftp_transport_selects_existing_backend_without_ssh() -> None:
    args = _parser().parse_args(["--transport", "ftp", "files", "ls", "/"])
    info = SimpleNamespace(host="ftp.example", port=22, username="user", password="pw", key_path="", timeout=5)
    with patch("truba_gui.cli.session.build_ssh_conn_info", return_value=info), patch(
        "truba_gui.cli.session.FTPFilesBackend", return_value=SimpleNamespace(close=lambda: None)
    ) as backend:
        session = CLISession.open(args)
    assert session.ssh is None
    backend.assert_called_once_with("ftp.example", port=21, username="user", password="pw", timeout=5.0)


def test_remote_commands_quote_arguments_and_preserve_result(capsys) -> None:
    args = _parser().parse_args(["sh", "--", "printf", "%s", "a b"])
    fake_ssh = SimpleNamespace(run=Mock(return_value=(7, "out", "err")))
    fake_session = SimpleNamespace(ssh=fake_ssh, close=lambda: None)
    with patch("truba_gui.cli.main.CLISession.open", return_value=fake_session) as opened:
        assert _run_sh(args) == 7
    opened.assert_called_once_with(args)
    fake_ssh.run.assert_called_once_with("printf %s 'a b'", timeout_s=30.0)
    assert capsys.readouterr().out == "out\n"


def test_remote_script_uses_bash_and_rejects_control_characters(capsys) -> None:
    args = _parser().parse_args(["run", "/tmp/run.sh", "a b"])
    fake_ssh = SimpleNamespace(run=Mock(return_value=(0, "ok", "")))
    fake_session = SimpleNamespace(ssh=fake_ssh, close=lambda: None)
    with patch("truba_gui.cli.main.CLISession.open", return_value=fake_session):
        assert _run_script(args) == 0
    fake_ssh.run.assert_called_once_with("bash /tmp/run.sh 'a b'", timeout_s=30.0)

    bad = _parser().parse_args(["sh", "--", "echo\nunsafe"])
    assert _run_sh(bad) == 2
    assert "control characters" in capsys.readouterr().err
