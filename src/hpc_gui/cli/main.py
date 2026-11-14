from __future__ import annotations

import argparse
import json as json
import os
import platform
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path as Path
from typing import Sequence

from hpc_gui.config.storage import (
    delete_profile as delete_profile,
    get_cli_external_access_enabled,
    load_profiles as load_profiles,
    upsert_profile as upsert_profile,
)
from hpc_gui.core.paths import app_data_dir as app_data_dir
from hpc_gui.cli.errors import ExitCode, emit_error
from hpc_gui.cli.session import (
    CLIConnectionError,
    CLISession,
    build_ssh_conn_info as build_ssh_conn_info,
    effective_profile_name as effective_profile_name,
    resolve_profile as resolve_profile,
)
from hpc_gui.services.connection_diagnostics import run_connection_diagnostics as run_connection_diagnostics
from hpc_gui.services.sftp_smoke import run_sftp_smoke as run_sftp_smoke
from hpc_gui.services.job_identity import is_valid_job_id
# The file runners resolve these through this module at call time (see cli/run_files.py).
from hpc_gui.cli.files import (  # noqa: F401
    download as download_files,
    upload as upload_files,
)
from hpc_gui.cli.jobs import emit_job_result as emit_job_result, jobs_backend as jobs_backend
from hpc_gui.cli.parser import (ROOT_ALIASES as ROOT_ALIASES,
                             _FullHelpArgumentParser as _FullHelpArgumentParser, _parser as _parser)
from hpc_gui.cli.run_profile import _run_profile as _run_profile
from hpc_gui.cli.run_files import _run_files as _run_files
from hpc_gui.cli.run_jobs import _run_jobs as _run_jobs
from hpc_gui.cli.run_doctor import _run_doctor as _run_doctor
from hpc_gui.cli.support import (
    _emit as _emit,
    _emit_remote_result as _emit_remote_result,
    _force_utf8_output as _force_utf8_output,
    _jobs_username as _jobs_username,
    _local_sha256 as _local_sha256,
    _normalize_alias_argv as _normalize_alias_argv,
    _profile_system_settings as _profile_system_settings,
    _provided_profile_fields as _provided_profile_fields,
    _requires_remote_session as _requires_remote_session,
    _safe_profile as _safe_profile,
    _validate_remote_tokens as _validate_remote_tokens,
    _walk_parser as _walk_parser,
)
CLI_VERSION = "1.5.9"



def _is_valid_job_id(value: str) -> bool:
    """Return whether a job ID is a safe plain, array, het, or step identifier.

    Accepts plain IDs, array task/range IDs, heterogeneous components, and
    common step suffixes while rejecting shell metacharacters.
    """
    return is_valid_job_id(value)


def _run_commands(args: argparse.Namespace) -> int:
    tree = _walk_parser(_parser(), [])
    exit_codes = {code.name: int(code.value) for code in ExitCode}
    payload = {
        "commands": tree,
        "aliases": [
            {"path": alias, "alias_for": " ".join(target)}
            for alias, target in sorted(ROOT_ALIASES.items())
        ],
        "exit_codes": exit_codes,
    }
    if args.format == "json":
        _emit(payload, output_format="json", quiet=args.quiet)
        return ExitCode.SUCCESS
    if args.quiet:
        return ExitCode.SUCCESS
    for entry in tree:
        print(f"{entry['path']}: {entry['help']}")
        for opt in entry["options"]:
            print(f"    {', '.join(opt['flags'])}  {opt['help']}")
    print("Aliases:")
    for alias, target in sorted(ROOT_ALIASES.items()):
        print(f"  {alias}: {' '.join(target)}")
    print()
    print("Exit codes:")
    for name, value in exit_codes.items():
        print(f"  {value}  {name}")
    return ExitCode.SUCCESS


def _run_edit(args: argparse.Namespace) -> int:
    session = None
    temporary = None
    try:
        session = CLISession.open(args)
        before = session.files.sha256(args.remote_path)
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.basename(args.remote_path))
        temporary = handle.name
        handle.close()
        session.files.download(args.remote_path, temporary)
        editor = args.editor or os.environ.get("TRUBA_EDITOR") or os.environ.get("EDITOR")
        if not editor or "\x00" in editor:
            raise RuntimeError("No editor configured; use --editor PROGRAM or set TRUBA_EDITOR.")
        command = shlex.split(editor, posix=False)
        result = subprocess.run([*command, temporary], check=False)
        if result.returncode:
            raise RuntimeError(f"Editor exited with code {result.returncode}.")
        if _local_sha256(temporary) == before:
            _emit({"remote_path": args.remote_path, "changed": False, "status": "unchanged"}, output_format=args.format, quiet=args.quiet)
            return ExitCode.SUCCESS
        if session.files.sha256(args.remote_path) != before:
            raise RuntimeError("Remote file changed while it was being edited; upload was refused.")
        session.files.upload(temporary, args.remote_path)
        if args.verify and session.files.sha256(args.remote_path) != _local_sha256(temporary):
            raise RuntimeError("Remote edit verification failed: uploaded content does not match.")
        _emit({"remote_path": args.remote_path, "changed": True, "status": "updated"}, output_format=args.format, quiet=args.quiet)
        return ExitCode.SUCCESS
    except CLIConnectionError as exc:
        emit_error(str(exc), exit_code=ExitCode.CONNECTION, output_format=args.format)
        return ExitCode.CONNECTION
    except Exception as exc:
        emit_error(f"Remote edit failed: {exc}", exit_code=ExitCode.OPERATION_FAILED, output_format=args.format)
        return ExitCode.OPERATION_FAILED
    finally:
        if session is not None:
            session.close()
        if temporary:
            try:
                os.unlink(temporary)
            except OSError:
                pass


def _run_remote_command(args: argparse.Namespace, command: str) -> int:
    session = None
    try:
        session = CLISession.open(args)
        if session.ssh is None:
            raise CLIConnectionError("This command requires --transport sftp.")
        return _emit_remote_result(*session.ssh.run(command, timeout_s=args.timeout), args)
    except CLIConnectionError as exc:
        emit_error(str(exc), exit_code=ExitCode.CONNECTION, output_format=args.format)
        return ExitCode.CONNECTION
    except ValueError as exc:
        emit_error(str(exc), exit_code=ExitCode.USAGE, output_format=args.format)
        return ExitCode.USAGE
    except Exception as exc:
        emit_error(f"Remote command failed: {exc}", exit_code=ExitCode.OPERATION_FAILED, output_format=args.format)
        return ExitCode.OPERATION_FAILED
    finally:
        if session is not None:
            session.close()


def _run_sh(args: argparse.Namespace) -> int:
    command = list(args.command)
    if command[:1] == ["--"]:
        command = command[1:]
    try:
        _validate_remote_tokens(command)
        return _run_remote_command(args, shlex.join(command))
    except ValueError as exc:
        emit_error(str(exc), exit_code=ExitCode.USAGE, output_format=args.format)
        return ExitCode.USAGE


def _run_script(args: argparse.Namespace) -> int:
    tokens = ["bash", args.remote_script, *args.arguments]
    try:
        _validate_remote_tokens(tokens)
        return _run_remote_command(args, shlex.join(tokens))
    except ValueError as exc:
        emit_error(str(exc), exit_code=ExitCode.USAGE, output_format=args.format)
        return ExitCode.USAGE


def _run_terminal(args: argparse.Namespace) -> int:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        emit_error("terminal requires an interactive terminal.", exit_code=ExitCode.USAGE, output_format=args.format)
        return ExitCode.USAGE
    session = None
    terminal_started = False
    try:
        profile = str(getattr(args, "profile", None) or "default profile")
        print(
            f"Connecting to {profile}; authenticating and opening the remote terminal...",
            file=sys.stderr,
            flush=True,
        )
        session = CLISession.open(args)
        if session.ssh is None:
            raise CLIConnectionError("This command requires --transport sftp.")
        session.ssh.resize_shell_pty(args.cols, args.rows)
        from hpc_gui.cli.terminal_input import terminal_key_reader

        print(
            "SSH connected. Remote terminal is ready; use Ctrl+Enter for dialog buttons, Ctrl+C to close.",
            file=sys.stderr,
            flush=True,
        )
        with terminal_key_reader() as read_key:
            terminal_started = True
            while True:
                key = read_key()
                if key == "\x03":
                    print("Closing remote terminal...", file=sys.stderr, flush=True)
                    break
                if key and not session.ssh.send_shell_input(key):
                    break
                if not key and not _shell_channel_is_active(
                    getattr(session.ssh, "_shell_channel", None)
                ):
                    break
        return ExitCode.SUCCESS
    except KeyboardInterrupt:
        print("Terminal connection cancelled.", file=sys.stderr, flush=True)
        return 130
    except CLIConnectionError as exc:
        emit_error(str(exc), exit_code=ExitCode.CONNECTION, output_format=args.format)
        return ExitCode.CONNECTION
    except Exception as exc:
        emit_error(f"Terminal failed: {exc}", exit_code=ExitCode.OPERATION_FAILED, output_format=args.format)
        return ExitCode.OPERATION_FAILED
    finally:
        if session is not None:
            session.close()
        if terminal_started and sys.stdout.isatty():
            # Remote full-screen programs can leave the local console in an
            # alternate screen or hide its cursor when the SSH channel closes.
            sys.stdout.write("\x1b[0m\x1b[?25h\x1b[?1049l\r\n")
            sys.stdout.flush()


def _shell_channel_is_active(channel) -> bool:
    return channel is not None and not getattr(channel, "closed", False)


def _run_interactive(args: argparse.Namespace) -> int:
    if args.format == "json" or not sys.stdin.isatty():
        emit_error("interactive requires a text-mode terminal.", exit_code=ExitCode.USAGE, output_format=args.format)
        return ExitCode.USAGE
    while True:
        try:
            line = input("hpc> ")
        except EOFError:
            return ExitCode.SUCCESS
        if line.strip().lower() in {"exit", "quit"}:
            return ExitCode.SUCCESS
        if not line.strip():
            continue
        try:
            nested = shlex.split(line)
        except ValueError as exc:
            print(f"parse error: {exc}", file=sys.stderr)
            continue
        if nested[:1] == ["interactive"]:
            print("interactive cannot be nested", file=sys.stderr)
            continue
        run_cli(nested)


def run_cli(argv: Sequence[str] | None = None, *, default_group: str | None = None) -> int:
    _force_utf8_output()
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    args = _parser().parse_args(_normalize_alias_argv(raw_argv))
    if args.group is None and default_group is not None:
        args.group = default_group
    if args.group in (None, "gui"):
        # Keep the selected GUI runtime and its widgets out of CLI startup.
        from hpc_gui.cli.gui import launch_gui

        if args.group == "gui":
            sys.argv = [sys.argv[0]]
        return launch_gui()
    if args.group == "version":
        _emit(
            {"version": CLI_VERSION, "name": "hpc-client-gui", "python": platform.python_version()},
            output_format=args.format,
            quiet=args.quiet,
        )
        return ExitCode.SUCCESS
    if args.group == "commands":
        return _run_commands(args)
    if _requires_remote_session(args) and not get_cli_external_access_enabled():
        emit_error(
            "Remote CLI access is disabled. Enable \"Allow external CLI access to remote commands\" in Settings to use this command.",
            exit_code=ExitCode.OPERATION_FAILED,
            output_format=args.format,
        )
        return ExitCode.OPERATION_FAILED
    if args.group == "profile":
        return _run_profile(args)
    if args.group == "doctor":
        return _run_doctor(args)
    if args.group == "interactive":
        return _run_interactive(args)
    if args.group == "sh":
        return _run_sh(args)
    if args.group == "run":
        return _run_script(args)
    if args.group == "terminal":
        return _run_terminal(args)
    if args.group == "files":
        return _run_files(args)
    if args.group == "edit":
        return _run_edit(args)
    if args.group == "jobs":
        return _run_jobs(args)
    emit_error(
        f"Unsupported command: {args.group}",
        exit_code=ExitCode.USAGE,
        output_format=args.format,
    )
    return ExitCode.USAGE
