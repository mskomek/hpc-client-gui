from __future__ import annotations
import argparse
from hpc_gui.cli.errors import ExitCode, emit_error
from hpc_gui.cli.session import CLIConnectionError, CLISession
from hpc_gui.cli.files import download as download_files, upload as upload_files
from ._shared import _emit

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
