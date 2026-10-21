from __future__ import annotations
import argparse
import json
import platform
import sys
from pathlib import Path
from hpc_gui.config.storage import load_profiles
from hpc_gui.core.paths import app_data_dir
from hpc_gui.cli.errors import ExitCode, emit_error
from hpc_gui.cli.session import CLIConnectionError, CLISession, build_ssh_conn_info
from hpc_gui.services.connection_diagnostics import run_connection_diagnostics
from hpc_gui.services.sftp_smoke import run_sftp_smoke
from ._shared import _emit

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
