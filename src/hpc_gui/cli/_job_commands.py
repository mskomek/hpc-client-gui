from __future__ import annotations
import argparse
from hpc_gui.cli.errors import ExitCode, emit_error
from hpc_gui.cli.session import CLIConnectionError, CLISession
from hpc_gui.cli.jobs import emit_job_result, jobs_backend
from ._shared import _is_valid_job_id, _jobs_username, _profile_system_settings

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
        # Keep the scheduler's exit status: a failed command must not be
        # reported as a successful result with the error text in its place.
        command_result = None
        if args.jobs_command == "list":
            command_result = backend.squeue_result(_jobs_username(args))
        elif args.jobs_command == "status":
            command_result = backend.scontrol_show_job_result(args.job_id)
        elif args.jobs_command == "accounting":
            command_result = backend.sacct_result(_jobs_username(args))
        elif args.jobs_command == "submit":
            command_result = backend.sbatch_result(str(args.script))
        elif args.jobs_command == "cancel":
            command_result = backend.scancel_result(str(args.job_id))
        else:
            result = backend.lssrv()

        if command_result is not None:
            if not command_result.ok:
                emit_error(
                    command_result.message,
                    exit_code=ExitCode.OPERATION_FAILED,
                    output_format=args.format,
                )
                return ExitCode.OPERATION_FAILED
            if args.jobs_command == "cancel":
                result = command_result.stdout.strip() or "OK"
            else:
                result = command_result.text
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
