from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Any, Sequence

from truba_gui.config.storage import load_profiles
from truba_gui.core.paths import app_data_dir
from truba_gui.cli.session import CLIConnectionError, CLISession
from truba_gui.cli.files import download as download_files, upload as upload_files


CLI_VERSION = "1.1.13"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hpc-client-gui",
        description="HPC Client GUI CLI and GUI launcher.",
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
    parser.add_argument("--user", dest="username", help="SSH username override.")
    parser.add_argument("--key", dest="key_path", help="SSH private-key path override.")
    parser.add_argument("--password-stdin", action="store_true", help="Read the SSH password from stdin.")
    parser.add_argument("--strict-host-key", action="store_true", help="Reject unknown SSH host keys.")

    commands = parser.add_subparsers(dest="group")
    commands.add_parser("gui", help="Launch the desktop GUI.")
    commands.add_parser("version", help="Print version and build information.")

    profile = commands.add_parser("profile", help="Inspect saved connection profiles.")
    profile_commands = profile.add_subparsers(dest="profile_command", required=True)
    profile_commands.add_parser("list", help="List profile names without secrets.")
    show = profile_commands.add_parser("show", help="Show a profile without secrets.")
    show.add_argument("name")

    doctor = commands.add_parser("doctor", help="Run local diagnostics.")
    doctor_commands = doctor.add_subparsers(dest="doctor_command", required=True)
    doctor_commands.add_parser("environment", help="Inspect the local runtime environment.")
    doctor_commands.add_parser("connection", help="Connect and initialize SFTP.")

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
    download = file_commands.add_parser("download", help="Download a remote file or directory.")
    download.add_argument("remote_path")
    download.add_argument("local_path")
    download.add_argument("--recursive", action="store_true")
    download.add_argument("--mode", choices=("binary", "ascii", "auto"), default="binary")
    download.add_argument("--verify", action="store_true", help="Verify SHA-256 after download.")
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


def _run_profile(args: argparse.Namespace) -> int:
    profiles = load_profiles()
    if args.profile_command == "list":
        _emit([str(profile.get("name", "")) for profile in profiles], output_format=args.format, quiet=args.quiet)
        return 0
    selected = next((profile for profile in profiles if profile.get("name") == args.name), None)
    if selected is None:
        print(f"Profile not found: {args.name}", file=sys.stderr)
        return 1
    _emit(_safe_profile(selected), output_format=args.format, quiet=args.quiet)
    return 0


def _run_doctor(args: argparse.Namespace) -> int:
    if args.doctor_command == "connection":
        session = None
        try:
            session = CLISession.open(args)
            payload = {"status": "PASS", "profile": session.profile_name, "sftp": True}
            _emit(payload, output_format=args.format, quiet=args.quiet)
            return 0
        except CLIConnectionError as exc:
            print(str(exc), file=sys.stderr)
            return 3
        finally:
            if session is not None:
                session.close()
    if args.doctor_command != "environment":
        print(f"Unsupported doctor command: {args.doctor_command}", file=sys.stderr)
        return 2
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
    return 0


def _run_files(args: argparse.Namespace) -> int:
    if args.files_command == "rm" and not args.yes:
        print("Refusing to remove remote data without --yes.", file=sys.stderr)
        return 2
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
            size, mtime = session.files.stat(path)
            payload = {
                "path": path,
                "type": "directory" if session.files.is_dir(path) else "file",
                "size": size,
                "mtime": mtime,
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
            print(f"Unsupported files command: {args.files_command}", file=sys.stderr)
            return 2
        _emit(payload, output_format=args.format, quiet=args.quiet)
        return 0
    except CLIConnectionError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except Exception as exc:
        print(f"File operation failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if session is not None:
            session.close()


def run_cli(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    if args.group in (None, "gui"):
        # Keep QApplication and all widgets out of the CLI import path.
        from truba_gui.app import main as gui_main

        if args.group == "gui":
            sys.argv = [sys.argv[0]]
        return int(gui_main())
    if args.group == "version":
        _emit(
            {"version": CLI_VERSION, "name": "hpc-client-gui", "python": platform.python_version()},
            output_format=args.format,
            quiet=args.quiet,
        )
        return 0
    if args.group == "profile":
        return _run_profile(args)
    if args.group == "doctor":
        return _run_doctor(args)
    if args.group == "files":
        return _run_files(args)
    print(f"Unsupported command: {args.group}", file=sys.stderr)
    return 2
