from __future__ import annotations
import argparse
from hpc_gui.config.storage import delete_profile, load_profiles, upsert_profile
from hpc_gui.cli.errors import ExitCode, emit_error
from hpc_gui.cli.session import CLIConnectionError, CLISession, resolve_profile
from ._shared import _emit, _provided_profile_fields, _safe_profile

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
