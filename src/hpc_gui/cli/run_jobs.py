"""The jobs command runner, split out of cli/main.py."""

from __future__ import annotations

import argparse


def _main():
    """Resolve the CLI main module at call time so its patched names stay effective."""
    from hpc_gui.cli import main as cli_main

    return cli_main


def _run_jobs(args: argparse.Namespace) -> int:
    main = _main()
    if args.jobs_command not in ("list", "status", "accounting", "lssrv", "submit", "cancel"):
        main.emit_error(
            f"Unsupported jobs command: {args.jobs_command}",
            exit_code=main.ExitCode.USAGE,
            output_format=args.format,
        )
        return main.ExitCode.USAGE
    if args.jobs_command == "submit" and not args.yes:
        main.emit_error(
            "Refusing to submit a job without --yes.",
            exit_code=main.ExitCode.USAGE,
            output_format=args.format,
        )
        return main.ExitCode.USAGE
    if args.jobs_command == "cancel" and not args.yes:
        main.emit_error(
            "Refusing to cancel a job without --yes.",
            exit_code=main.ExitCode.USAGE,
            output_format=args.format,
        )
        return main.ExitCode.USAGE
    if args.jobs_command == "cancel" and not main._is_valid_job_id(str(args.job_id)):
        main.emit_error(
            f"Invalid job ID: {args.job_id}",
            exit_code=main.ExitCode.USAGE,
            output_format=args.format,
        )
        return main.ExitCode.USAGE
    session = None
    try:
        session = main.CLISession.open(args)
        backend = main.jobs_backend(session, system_settings=main._profile_system_settings(args))
        # Keep the scheduler's exit status: a failed command must not be
        # reported as a successful result with the error text in its place.
        command_result = None
        if args.jobs_command == "list":
            command_result = backend.squeue_result(main._jobs_username(args))
        elif args.jobs_command == "status":
            command_result = backend.scontrol_show_job_result(args.job_id)
        elif args.jobs_command == "accounting":
            command_result = backend.sacct_result(main._jobs_username(args))
        elif args.jobs_command == "submit":
            command_result = backend.sbatch_result(str(args.script))
        elif args.jobs_command == "cancel":
            command_result = backend.scancel_result(str(args.job_id))
        else:
            result = backend.lssrv()

        if command_result is not None:
            if not command_result.ok:
                main.emit_error(
                    command_result.message,
                    exit_code=main.ExitCode.OPERATION_FAILED,
                    output_format=args.format,
                )
                return main.ExitCode.OPERATION_FAILED
            if args.jobs_command == "cancel":
                result = command_result.stdout.strip() or "OK"
            else:
                result = command_result.text
        return main.emit_job_result(result, output_format=args.format, quiet=args.quiet)
    except main.CLIConnectionError as exc:
        main.emit_error(str(exc), exit_code=main.ExitCode.CONNECTION, output_format=args.format)
        return main.ExitCode.CONNECTION
    except Exception as exc:
        main.emit_error(
            f"Jobs operation failed: {exc}",
            exit_code=main.ExitCode.OPERATION_FAILED,
            output_format=args.format,
        )
        return main.ExitCode.OPERATION_FAILED
    finally:
        if session is not None:
            session.close()
