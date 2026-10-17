from __future__ import annotations
import argparse
import sys
from typing import Any
from hpc_gui.cli.files import IF_EXISTS_CHOICES
from hpc_gui.cli.errors import ExitCode
from ._contracts import ROOT_ALIASES
from ._shared import _emit

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
