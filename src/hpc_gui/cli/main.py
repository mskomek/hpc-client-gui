from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

from hpc_gui.config.storage import (
    delete_profile,
    get_cli_external_access_enabled,
    load_profiles,
    upsert_profile,
)
from hpc_gui.core.paths import app_data_dir
from hpc_gui.cli.errors import ExitCode, emit_error
from hpc_gui.cli.session import (
    CLIConnectionError,
    CLISession,
    build_ssh_conn_info,
    effective_profile_name,
    resolve_profile,
)
from hpc_gui.services.connection_diagnostics import run_connection_diagnostics
from hpc_gui.services.sftp_smoke import run_sftp_smoke
from hpc_gui.cli.files import IF_EXISTS_CHOICES, download as download_files, upload as upload_files
from hpc_gui.cli.jobs import emit_job_result, jobs_backend


CLI_VERSION = "1.4.1"

ROOT_ALIASES = {
    "put": ("files", "upload"), "get": ("files", "download"),
    "ls": ("files", "ls"), "stat": ("files", "stat"),
    "checksum": ("files", "checksum"), "mkdir": ("files", "mkdir"),
    "cp": ("files", "cp"), "mv": ("files", "mv"), "rm": ("files", "rm"),
    "squeue": ("jobs", "list"), "scontrol": ("jobs", "status"),
    "sacct": ("jobs", "accounting"), "lssrv": ("jobs", "lssrv"),
    "sbatch": ("jobs", "submit"), "scancel": ("jobs", "cancel"),
}

_JOBS_JOB_ID_RE = re.compile(r"\d+(?:[_.]\d+)?\Z")


class _FullHelpArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_help(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def _parser() -> argparse.ArgumentParser:
    parser = _FullHelpArgumentParser(
        prog="hpc-client-gui",
        description="HPC Client GUI CLI and GUI launcher.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  hpc-client-gui --profile arf files ls /home\n"
            "  hpc-client-gui --profile arf jobs submit run.sh --yes\n"
            "  hpc-client-gui --profile arf doctor connection\n"
            "  hpc-client-gui --format json commands\n"
        ),
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format for command results.",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress non-error output.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose diagnostics.")
    parser.add_argument("--timeout", type=float, default=30.0, help="Default operation timeout in seconds.")
    parser.add_argument("--profile", help="Saved connection profile name.")
    parser.add_argument("--host", help="SSH host override.")
    parser.add_argument("--port", type=int, help="SSH port override.")
    parser.add_argument("--transport", choices=("sftp", "ftp"), default="sftp", help="File transport (default: sftp).")
    parser.add_argument("--user", dest="username", help="SSH username override.")
    parser.add_argument("--key", dest="key_path", help="SSH private-key path override.")
    parser.add_argument("--password-stdin", action="store_true", help="Read the SSH password from stdin.")
    parser.add_argument(
        "--password-prompt",
        action="store_true",
        help="Prompt for the SSH password without echoing it (terminal only).",
    )
    parser.add_argument(
        "--no-saved-password",
        action="store_true",
        help="Do not use a profile's saved DPAPI-protected secret; require --password-stdin instead.",
    )
    parser.add_argument("--strict-host-key", action="store_true", help="Reject unknown SSH host keys.")

    commands = parser.add_subparsers(dest="group")
    commands.add_parser("gui", help="Launch the desktop GUI.")
    commands.add_parser("version", help="Print version and build information.")
    commands.add_parser("commands", help="Print the full command inventory (for scripting and automation).")

    profile = commands.add_parser("profile", help="Inspect saved connection profiles.")
    profile_commands = profile.add_subparsers(dest="profile_command", required=True)
    profile_commands.add_parser("list", help="List profile names without secrets.")
    show = profile_commands.add_parser("show", help="Show a profile without secrets.")
    show.add_argument("name")

    create = profile_commands.add_parser("create", help="Create a profile with non-sensitive fields only.")
    create.add_argument("name")
    create.add_argument("--host", help="SSH host.")
    create.add_argument("--port", type=int, help="SSH port.")
    create.add_argument("--user", dest="username", help="SSH username.")
    create.add_argument("--key", dest="key_path", help="SSH private-key path.")
    create.add_argument("--host-key-policy", choices=("accept-new", "strict"), help="Host-key acceptance policy.")

    update = profile_commands.add_parser("update", help="Update non-sensitive fields of a profile.")
    update.add_argument("name")
    update.add_argument("--host", help="SSH host.")
    update.add_argument("--port", type=int, help="SSH port.")
    update.add_argument("--user", dest="username", help="SSH username.")
    update.add_argument("--key", dest="key_path", help="SSH private-key path.")
    update.add_argument("--host-key-policy", choices=("accept-new", "strict"), help="Host-key acceptance policy.")

    delete = profile_commands.add_parser("delete", help="Delete a profile.")
    delete.add_argument("name")
    delete.add_argument("--yes", action="store_true", help="Confirm profile removal.")

    test = profile_commands.add_parser("test", help="Verify a saved profile connection.")
    test.add_argument("name")

    doctor = commands.add_parser("doctor", help="Run local diagnostics.")
    doctor_commands = doctor.add_subparsers(dest="doctor_command", required=True)
    doctor_commands.add_parser("environment", help="Inspect the local runtime environment.")
    doctor_commands.add_parser("connection", help="Connect and initialize SFTP.")
    smoke = doctor_commands.add_parser("smoke", help="Round-trip a smoke file over SFTP.")
    smoke.add_argument("--keep", action="store_true", help="Preserve the remote smoke directory.")
    smoke.add_argument("--artifact", help="Write the smoke result JSON artifact to a local path.")

    files = commands.add_parser("files", help="Remote SFTP file operations.")
    file_commands = files.add_subparsers(dest="files_command", required=True)
    ls = file_commands.add_parser("ls", help="List a remote directory.")
    ls.add_argument("path", nargs="?", default=".")
    stat = file_commands.add_parser("stat", help="Show remote file metadata.")
    stat.add_argument("path")
    checksum = file_commands.add_parser("checksum", help="Show remote SHA-256.")
    checksum.add_argument("path")
    mkdir = file_commands.add_parser("mkdir", help="Create a remote directory.")
    mkdir.add_argument("path")
    upload = file_commands.add_parser("upload", help="Upload a local file or directory.")
    upload.add_argument("local_path")
    upload.add_argument("remote_path")
    upload.add_argument("--recursive", action="store_true")
    upload.add_argument("--mode", choices=("binary", "ascii", "auto"), default="binary")
    upload.add_argument("--verify", action="store_true", help="Verify SHA-256 after upload.")
    upload.add_argument(
        "--if-exists",
        choices=IF_EXISTS_CHOICES,
        default="overwrite",
        help="Action when the remote destination already exists.",
    )
    download = file_commands.add_parser("download", help="Download a remote file or directory.")
    download.add_argument("remote_path")
    download.add_argument("local_path")
    download.add_argument("--recursive", action="store_true")
    download.add_argument("--mode", choices=("binary", "ascii", "auto"), default="binary")
    download.add_argument("--verify", action="store_true", help="Verify SHA-256 after download.")
    download.add_argument(
        "--if-exists",
        choices=IF_EXISTS_CHOICES,
        default="overwrite",
        help="Action when the local destination already exists.",
    )
    copy = file_commands.add_parser("cp", help="Copy a remote file or directory.")
    copy.add_argument("source")
    copy.add_argument("destination")
    copy.add_argument("--recursive", action="store_true")
    move = file_commands.add_parser("mv", help="Move or rename a remote path.")
    move.add_argument("source")
    move.add_argument("destination")
    remove = file_commands.add_parser("rm", help="Remove a remote path.")
    remove.add_argument("path")
    remove.add_argument("--recursive", action="store_true")
    remove.add_argument("--yes", action="store_true", help="Confirm destructive removal.")

    edit = commands.add_parser("edit", help="Edit a remote file with a local editor.")
    edit.add_argument("remote_path")
    edit.add_argument("--editor", help="Editor command; defaults to TRUBA_EDITOR or EDITOR.")
    edit.add_argument("--verify", action="store_true", help="Verify SHA-256 after upload.")

    shell = commands.add_parser("sh", help="Run a quoted command on the remote shell.")
    shell.add_argument("command", nargs=argparse.REMAINDER, help="COMMAND [ARG ...]; prefix with --.")
    run = commands.add_parser("run", help="Run a remote script with bash.")
    run.add_argument("remote_script")
    run.add_argument("arguments", nargs=argparse.REMAINDER)
    terminal = commands.add_parser("terminal", help="Open an interactive remote terminal.")
    terminal.add_argument("--cols", type=int, default=120)
    terminal.add_argument("--rows", type=int, default=32)
    commands.add_parser("interactive", help="Open an interactive CLI prompt.")

    jobs = commands.add_parser("jobs", help="Inspect scheduler jobs and cluster state.")
    jobs_command = jobs.add_subparsers(dest="jobs_command", required=True)
    jobs_command.add_parser("list", help="List the user's queued and running jobs.")
    status = jobs_command.add_parser("status", help="Show the state of a single job.")
    status.add_argument("job_id", help="Job ID to inspect.")
    jobs_command.add_parser("accounting", help="Show accounting data for the user's jobs.")
    jobs_command.add_parser("lssrv", help="Show login-node cluster state.")
    submit = jobs_command.add_parser("submit", help="Submit a batch script to the scheduler.")
    submit.add_argument("script", help="Remote batch script path to submit.")
    submit.add_argument("--yes", action="store_true", help="Confirm submission of the batch script.")
    cancel = jobs_command.add_parser("cancel", help="Cancel a queued or running job.")
    cancel.add_argument("job_id", help="Job ID to cancel.")
    cancel.add_argument("--yes", action="store_true", help="Confirm cancellation of the job.")
    return parser


def _emit(payload: Any, *, output_format: str, quiet: bool = False) -> None:
    if quiet:
        return
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(value, (dict, list)):
                print(f"{key}: {json.dumps(value, ensure_ascii=False)}")
            else:
                print(f"{key}: {value}")
        return
    if isinstance(payload, list):
        for value in payload:
            print(value)
        return
    print(payload)


def _walk_parser(parser: argparse.ArgumentParser, path: list[str]) -> list[dict[str, Any]]:
    options = []
    subparsers_action = None
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            subparsers_action = action
            continue
        if not action.option_strings:
            continue
        options.append({"flags": list(action.option_strings), "help": action.help or ""})
    entries = [{
        "path": " ".join(path) if path else parser.prog,
        "help": parser.description or "",
        "options": options,
    }]
    if subparsers_action:
        for name, subparser in subparsers_action.choices.items():
            entries.extend(_walk_parser(subparser, path + [name]))
    return entries


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


def _requires_remote_session(args: argparse.Namespace) -> bool:
    group = getattr(args, "group", None)
    if group in ("files", "jobs", "edit", "sh", "run", "terminal"):
        return True
    if group == "profile" and getattr(args, "profile_command", None) == "test":
        return True
    if group == "doctor" and getattr(args, "doctor_command", None) in ("connection", "smoke"):
        return True
    return False


def _safe_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Return profile metadata while excluding all secret fields."""
    allowed = (
        "name",
        "host",
        "port",
        "username",
        "key_path",
        "host_key_policy",
        "x11_forwarding",
        "system",
    )
    return {key: profile.get(key) for key in allowed if key in profile}


_PROFILE_SLALAR_FIELDS = ("host", "port", "username", "key_path", "host_key_policy")


def _provided_profile_fields(args: argparse.Namespace) -> dict[str, Any]:
    """Lollect the non-sensitive scalar profile fields explicitly provided."""
    provided: dict[str, Any] = {}
    for key in _PROFILE_SLALAR_FIELDS:
        value = getattr(args, key, None)
        if value not in (None, ""):
            provided[key] = value
    return provided


def _run_profile(args: argparse.Namespace) -> int:
    if args.profile_command == "create":
        record = {"name": args.name}
        record.update(_provided_profile_fields(args))
        try:
            upsert_profile(record)
        except ValueError as exc:
            emit_error(str(exc), exit_code=ExitCode.USAGE, output_format=args.format)
            return ExitCode.USAGE
        _emit(_safe_profile(record), output_format=args.format, quiet=args.quiet)
        return ExitCode.SUCCESS

    if args.profile_command == "update":
        provided = _provided_profile_fields(args)
        if not provided:
            emit_error(
                "profile update requires at least one field "
                "(--host, --port, --user, --key, --host-key-policy).",
                exit_code=ExitCode.USAGE,
                output_format=args.format,
            )
            return ExitCode.USAGE
        existing = resolve_profile(args.name)
        if existing is None:
            emit_error(
                f"Profile not found: {args.name}. Create it with 'profile create {args.name}'.",
                exit_code=ExitCode.OPERATION_FAILED,
                output_format=args.format,
            )
            return ExitCode.OPERATION_FAILED
        updated = dict(existing)
        updated.update(provided)
        upsert_profile(updated)
        _emit(_safe_profile(updated), output_format=args.format, quiet=args.quiet)
        return ExitCode.SUCCESS

    if args.profile_command == "delete":
        if not args.yes:
            emit_error(
                f"Refusing to delete profile '{args.name}' without --yes.",
                exit_code=ExitCode.USAGE,
                output_format=args.format,
            )
            return ExitCode.USAGE
        if resolve_profile(args.name) is None:
            emit_error(
                f"Profile not found: {args.name}. Nothing to delete.",
                exit_code=ExitCode.OPERATION_FAILED,
                output_format=args.format,
            )
            return ExitCode.OPERATION_FAILED
        delete_profile(args.name)
        _emit(
            {"operation": "delete", "name": args.name, "status": "ok"},
            output_format=args.format,
            quiet=args.quiet,
        )
        return ExitCode.SUCCESS

    if args.profile_command == "test":
        if resolve_profile(args.name) is None:
            emit_error(
                f"Profile not found: {args.name}. Create it with 'profile create {args.name}'.",
                exit_code=ExitCode.OPERATION_FAILED,
                output_format=args.format,
            )
            return ExitCode.OPERATION_FAILED
        args.profile = args.name
        session = None
        try:
            session = CLISession.open(args)
        except CLIConnectionError as exc:
            _emit(
                {"status": "FAIL", "profile": args.name, "message": str(exc)},
                output_format=args.format,
                quiet=args.quiet,
            )
            return ExitCode.CONNECTION
        finally:
            if session is not None:
                session.close()
        _emit(
            {"status": "PASS", "profile": args.name, "sftp": True},
            output_format=args.format,
            quiet=args.quiet,
        )
        return ExitCode.SUCCESS

    if args.profile_command == "list":
        _emit(
            [str(profile.get("name", "")) for profile in load_profiles()],
            output_format=args.format,
            quiet=args.quiet,
        )
        return ExitCode.SUCCESS
    selected = resolve_profile(args.name)
    if selected is None:
        emit_error(
            f"Profile not found: {args.name}",
            exit_code=ExitCode.OPERATION_FAILED,
            output_format=args.format,
        )
        return ExitCode.OPERATION_FAILED
    _emit(_safe_profile(selected), output_format=args.format, quiet=args.quiet)
    return ExitCode.SUCCESS


def _run_doctor(args: argparse.Namespace) -> int:
    if args.doctor_command == "connection":
        try:
            info = build_ssh_conn_info(args)
        except CLIConnectionError as exc:
            emit_error(str(exc), exit_code=ExitCode.CONNECTION, output_format=args.format)
            return ExitCode.CONNECTION
        payload = run_connection_diagnostics(info)
        payload["profile"] = getattr(args, "profile", "") or ""
        _emit(payload, output_format=args.format, quiet=args.quiet)
        if all(stage.get("status") == "PASS" for stage in payload.get("stages", {}).values()):
            return ExitCode.SUCCESS
        return ExitCode.CONNECTION
    if args.doctor_command == "smoke":
        session = None
        try:
            session = CLISession.open(args)
            payload = run_sftp_smoke(session.files, cleanup=not args.keep)
        except CLIConnectionError as exc:
            emit_error(str(exc), exit_code=ExitCode.CONNECTION, output_format=args.format)
            return ExitCode.CONNECTION
        finally:
            if session is not None:
                session.close()
        payload["profile"] = getattr(args, "profile", "") or ""
        payload["cleanup_requested"] = bool(not args.keep)
        payload["schema"] = "sftp-smoke/1"
        _emit(payload, output_format=args.format, quiet=args.quiet)
        exit_code = ExitCode.SUCCESS if payload.get("status") == "PASS" else ExitCode.CONNECTION
        if args.artifact:
            try:
                Path(args.artifact).write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except OSError as exc:
                emit_error(
                    f"could not write smoke artifact: {exc}",
                    exit_code=ExitCode.OPERATION_FAILED,
                    output_format=args.format,
                )
                return ExitCode.OPERATION_FAILED
        return exit_code
    if args.doctor_command != "environment":
        emit_error(
            f"Unsupported doctor command: {args.doctor_command}",
            exit_code=ExitCode.USAGE,
            output_format=args.format,
        )
        return ExitCode.USAGE
    payload = {
        "status": "PASS",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "frozen": bool(getattr(sys, "frozen", False)),
        "executable": sys.executable,
        "config_dir": str(app_data_dir()),
        "profiles": len(load_profiles()),
    }
    _emit(payload, output_format=args.format, quiet=args.quiet)
    return ExitCode.SUCCESS


def _local_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _validate_remote_tokens(tokens: Sequence[str]) -> None:
    if not tokens or any(any(ord(char) < 32 for char in token) for token in tokens):
        raise ValueError("Remote command arguments must be non-empty and contain no control characters.")


def _emit_remote_result(code: int, stdout: str, stderr: str, args: argparse.Namespace) -> int:
    if args.format == "json":
        _emit({"stdout": stdout, "stderr": stderr, "exit_code": int(code)}, output_format="json", quiet=args.quiet)
    elif not args.quiet:
        if stdout:
            print(stdout, end="" if stdout.endswith("\n") else "\n")
        if stderr:
            print(stderr, end="" if stderr.endswith("\n") else "\n", file=sys.stderr)
    return int(code)


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
    try:
        session = CLISession.open(args)
        if session.ssh is None:
            raise CLIConnectionError("This command requires --transport sftp.")
        session.ssh.resize_shell_pty(args.cols, args.rows)
        for line in sys.stdin:
            if not session.ssh.send_shell_input(line):
                break
        return ExitCode.SUCCESS
    except CLIConnectionError as exc:
        emit_error(str(exc), exit_code=ExitCode.CONNECTION, output_format=args.format)
        return ExitCode.CONNECTION
    except Exception as exc:
        emit_error(f"Terminal failed: {exc}", exit_code=ExitCode.OPERATION_FAILED, output_format=args.format)
        return ExitCode.OPERATION_FAILED
    finally:
        if session is not None:
            session.close()


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


def _run_files(args: argparse.Namespace) -> int:
    if args.files_command == "rm" and not args.yes:
        emit_error(
            "Refusing to remove remote data without --yes.",
            exit_code=ExitCode.USAGE,
            output_format=args.format,
        )
        return ExitCode.USAGE
    session = None
    try:
        session = CLISession.open(args)
        if args.files_command == "ls":
            path = str(args.path)
            entries = session.files.listdir_entries(path)
            payload = [
                {
                    "name": entry.name,
                    "path": entry.path,
                    "type": "directory" if entry.is_dir else "file",
                    "size": entry.size,
                    "mtime": entry.mtime,
                    "mode": entry.mode,
                }
                for entry in entries
            ]
        elif args.files_command == "stat":
            path = str(args.path)
            entry = session.files.stat_entry(path)
            payload = {
                "name": entry.name,
                "path": entry.path,
                "type": "directory" if entry.is_dir else "file",
                "size": entry.size,
                "mtime": entry.mtime,
                "mode": entry.mode,
            }
        elif args.files_command == "checksum":
            path = str(args.path)
            payload = {"path": path, "sha256": session.files.sha256(path)}
        elif args.files_command == "mkdir":
            path = str(args.path)
            session.files.mkdir(path)
            payload = {"operation": "mkdir", "path": path, "status": "ok"}
        elif args.files_command == "upload":
            payload = upload_files(
                session.files,
                args.local_path,
                args.remote_path,
                recursive=args.recursive,
                mode=args.mode,
                verify=args.verify,
                quiet=args.quiet,
                if_exists=args.if_exists,
            )
        elif args.files_command == "download":
            payload = download_files(
                session.files,
                args.remote_path,
                args.local_path,
                recursive=args.recursive,
                mode=args.mode,
                verify=args.verify,
                quiet=args.quiet,
                if_exists=args.if_exists,
            )
        elif args.files_command == "cp":
            if session.files.is_dir(args.source) and not args.recursive:
                raise IsADirectoryError(f"{args.source} is a directory; use --recursive")
            session.files.copy(args.source, args.destination, recursive=args.recursive)
            payload = {"operation": "cp", "source": args.source, "destination": args.destination, "status": "ok"}
        elif args.files_command == "mv":
            session.files.move(args.source, args.destination)
            payload = {"operation": "mv", "source": args.source, "destination": args.destination, "status": "ok"}
        elif args.files_command == "rm":
            path = str(args.path)
            session.files.remove(path, recursive=args.recursive)
            payload = {"operation": "rm", "path": path, "status": "ok"}
        else:
            emit_error(
                f"Unsupported files command: {args.files_command}",
                exit_code=ExitCode.USAGE,
                output_format=args.format,
            )
            return ExitCode.USAGE
        _emit(payload, output_format=args.format, quiet=args.quiet)
        return ExitCode.SUCCESS
    except CLIConnectionError as exc:
        emit_error(str(exc), exit_code=ExitCode.CONNECTION, output_format=args.format)
        return ExitCode.CONNECTION
    except TimeoutError as exc:
        detail = str(exc).strip() or "remote operation timed out"
        emit_error(
            f"Operation timed out: {detail}",
            exit_code=ExitCode.TIMEOUT,
            output_format=args.format,
        )
        return ExitCode.TIMEOUT
    except (FileNotFoundError, NotADirectoryError) as exc:
        detail = getattr(exc, "filename", None) or str(exc)
        emit_error(
            f"Not found: {detail}",
            exit_code=ExitCode.OPERATION_FAILED,
            output_format=args.format,
        )
        return ExitCode.OPERATION_FAILED
    except PermissionError as exc:
        detail = getattr(exc, "filename", None) or str(exc)
        emit_error(
            f"Permission denied: {detail}",
            exit_code=ExitCode.OPERATION_FAILED,
            output_format=args.format,
        )
        return ExitCode.OPERATION_FAILED
    except Exception as exc:
        emit_error(
            f"File operation failed: {exc}",
            exit_code=ExitCode.OPERATION_FAILED,
            output_format=args.format,
        )
        return ExitCode.OPERATION_FAILED
    finally:
        if session is not None:
            session.close()


def _jobs_username(args: argparse.Namespace) -> str:
    """Resolve the target username for ``jobs list`` without consuming stdin.

    Mirrors the small, side-effect-free precedence used by
    ``build_ssh_conn_info``: an explicit ``args.username`` wins, otherwise the
    profile's username, otherwise an empty string.
    """
    profile_name = effective_profile_name(args)
    profile = resolve_profile(profile_name) if profile_name else None
    username = str(getattr(args, "username", "") or (profile or {}).get("username", "") or "")
    return username


def _profile_system_settings(args: argparse.Namespace) -> dict[str, Any] | None:
    """Resolve the selected profile's embedded system settings, if any.

    Saved profiles keep a resolved ``system`` snapshot; the CLI reuses it so
    site-specific commands (for example a ``lssrv`` status command) come from
    the profile rather than from generic built-in defaults.
    """
    profile_name = effective_profile_name(args)
    if not profile_name:
        return None
    profile = resolve_profile(profile_name)
    if not isinstance(profile, dict):
        return None
    system = profile.get("system")
    if not isinstance(system, dict):
        return None
    return {key: value for key, value in system.items() if isinstance(value, str)}


def _is_valid_job_id(value: str) -> bool:
    """Return whether a job ID is a safe plain, array-task, or step identifier.

    Accepts only digits, optionally followed by a single ``_`` or ``.`` and one
    or more further digits (for example ``12345``, ``12345_3``, ``12345.0``).
    """
    return bool(_JOBS_JOB_ID_RE.fullmatch(value))


def _run_jobs(args: argparse.Namespace) -> int:
    if args.jobs_command not in ("list", "status", "accounting", "lssrv", "submit", "cancel"):
        emit_error(
            f"Unsupported jobs command: {args.jobs_command}",
            exit_code=ExitCode.USAGE,
            output_format=args.format,
        )
        return ExitCode.USAGE
    if args.jobs_command == "submit" and not args.yes:
        emit_error(
            "Refusing to submit a job without --yes.",
            exit_code=ExitCode.USAGE,
            output_format=args.format,
        )
        return ExitCode.USAGE
    if args.jobs_command == "cancel" and not args.yes:
        emit_error(
            "Refusing to cancel a job without --yes.",
            exit_code=ExitCode.USAGE,
            output_format=args.format,
        )
        return ExitCode.USAGE
    if args.jobs_command == "cancel" and not _is_valid_job_id(str(args.job_id)):
        emit_error(
            f"Invalid job ID: {args.job_id}",
            exit_code=ExitCode.USAGE,
            output_format=args.format,
        )
        return ExitCode.USAGE
    session = None
    try:
        session = CLISession.open(args)
        backend = jobs_backend(session, system_settings=_profile_system_settings(args))
        if args.jobs_command == "list":
            result = backend.squeue(_jobs_username(args))
        elif args.jobs_command == "status":
            result = backend.scontrol_show_job(args.job_id)
        elif args.jobs_command == "accounting":
            result = backend.sacct(_jobs_username(args))
        elif args.jobs_command == "submit":
            result = backend.sbatch(str(args.script))
        elif args.jobs_command == "cancel":
            result = backend.scancel(str(args.job_id))
        else:
            result = backend.lssrv()
        return emit_job_result(result, output_format=args.format, quiet=args.quiet)
    except CLIConnectionError as exc:
        emit_error(str(exc), exit_code=ExitCode.CONNECTION, output_format=args.format)
        return ExitCode.CONNECTION
    except Exception as exc:
        emit_error(
            f"Jobs operation failed: {exc}",
            exit_code=ExitCode.OPERATION_FAILED,
            output_format=args.format,
        )
        return ExitCode.OPERATION_FAILED
    finally:
        if session is not None:
            session.close()


def _normalize_alias_argv(argv: Sequence[str]) -> list[str]:
    values = list(argv)
    value_options = {"--format", "--timeout", "--profile", "--host", "--port", "--user", "--key"}
    index = 0
    while index < len(values):
        token = values[index]
        if token in value_options:
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        target = ROOT_ALIASES.get(token)
        return [*values[:index], *(target or (token,)), *values[index + 1:]]
    return values


def run_cli(argv: Sequence[str] | None = None, *, default_group: str | None = None) -> int:
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    args = _parser().parse_args(_normalize_alias_argv(raw_argv))
    if args.group is None and default_group is not None:
        args.group = default_group
    if args.group in (None, "gui"):
        # Keep QApplication and all widgets out of the CLI import path.
        from hpc_gui.app import main as gui_main

        if args.group == "gui":
            sys.argv = [sys.argv[0]]
        return int(gui_main())
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
