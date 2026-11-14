"""The profile command runner, split out of cli/main.py."""

from __future__ import annotations

import argparse


def _main():
    """Resolve the CLI main module at call time so its patched names stay effective."""
    from hpc_gui.cli import main as cli_main

    return cli_main


def _run_profile(args: argparse.Namespace) -> int:
    main = _main()
    if args.profile_command == "create":
        record = {"name": args.name}
        record.update(main._provided_profile_fields(args))
        try:
            main.upsert_profile(record)
        except ValueError as exc:
            main.emit_error(str(exc), exit_code=main.ExitCode.USAGE, output_format=args.format)
            return main.ExitCode.USAGE
        main._emit(main._safe_profile(record), output_format=args.format, quiet=args.quiet)
        return main.ExitCode.SUCCESS

    if args.profile_command == "update":
        provided = main._provided_profile_fields(args)
        if not provided:
            main.emit_error(
                "profile update requires at least one field "
                "(--host, --port, --user, --key, --host-key-policy).",
                exit_code=main.ExitCode.USAGE,
                output_format=args.format,
            )
            return main.ExitCode.USAGE
        existing = main.resolve_profile(args.name)
        if existing is None:
            main.emit_error(
                f"Profile not found: {args.name}. Create it with 'profile create {args.name}'.",
                exit_code=main.ExitCode.OPERATION_FAILED,
                output_format=args.format,
            )
            return main.ExitCode.OPERATION_FAILED
        updated = dict(existing)
        updated.update(provided)
        main.upsert_profile(updated)
        main._emit(main._safe_profile(updated), output_format=args.format, quiet=args.quiet)
        return main.ExitCode.SUCCESS

    if args.profile_command == "delete":
        if not args.yes:
            main.emit_error(
                f"Refusing to delete profile '{args.name}' without --yes.",
                exit_code=main.ExitCode.USAGE,
                output_format=args.format,
            )
            return main.ExitCode.USAGE
        if main.resolve_profile(args.name) is None:
            main.emit_error(
                f"Profile not found: {args.name}. Nothing to delete.",
                exit_code=main.ExitCode.OPERATION_FAILED,
                output_format=args.format,
            )
            return main.ExitCode.OPERATION_FAILED
        main.delete_profile(args.name)
        main._emit(
            {"operation": "delete", "name": args.name, "status": "ok"},
            output_format=args.format,
            quiet=args.quiet,
        )
        return main.ExitCode.SUCCESS

    if args.profile_command == "test":
        if main.resolve_profile(args.name) is None:
            main.emit_error(
                f"Profile not found: {args.name}. Create it with 'profile create {args.name}'.",
                exit_code=main.ExitCode.OPERATION_FAILED,
                output_format=args.format,
            )
            return main.ExitCode.OPERATION_FAILED
        args.profile = args.name
        session = None
        try:
            session = main.CLISession.open(args)
        except main.CLIConnectionError as exc:
            main._emit(
                {"status": "FAIL", "profile": args.name, "message": str(exc)},
                output_format=args.format,
                quiet=args.quiet,
            )
            return main.ExitCode.CONNECTION
        finally:
            if session is not None:
                session.close()
        main._emit(
            {"status": "PASS", "profile": args.name, "sftp": True},
            output_format=args.format,
            quiet=args.quiet,
        )
        return main.ExitCode.SUCCESS

    if args.profile_command == "list":
        main._emit(
            [str(profile.get("name", "")) for profile in main.load_profiles()],
            output_format=args.format,
            quiet=args.quiet,
        )
        return main.ExitCode.SUCCESS
    selected = main.resolve_profile(args.name)
    if selected is None:
        main.emit_error(
            f"Profile not found: {args.name}",
            exit_code=main.ExitCode.OPERATION_FAILED,
            output_format=args.format,
        )
        return main.ExitCode.OPERATION_FAILED
    main._emit(main._safe_profile(selected), output_format=args.format, quiet=args.quiet)
    return main.ExitCode.SUCCESS
