"""Command-line entrypoint and public compatibility facade."""

from __future__ import annotations

import argparse
import platform
import sys
from typing import Sequence

from hpc_gui.config.storage import get_cli_external_access_enabled
from hpc_gui.cli.errors import ExitCode, emit_error
from hpc_gui.cli.session import (
    CLIConnectionError,
    CLISession,
    build_ssh_conn_info,
    effective_profile_name,
    resolve_profile,
)
from ._contracts import CLI_VERSION, ROOT_ALIASES
from ._shared import (
    _JOBS_JOB_ID_RE, _emit,
    _requires_remote_session, _safe_profile, _provided_profile_fields,
    _local_sha256, _validate_remote_tokens, _emit_remote_result,
    _jobs_username, _profile_system_settings, _is_valid_job_id,
    _normalize_alias_argv, _force_utf8_output,
)
from ._parser import _FullHelpArgumentParser, _parser, _walk_parser, _run_commands
from ._profile_commands import _run_profile
from ._doctor_commands import _run_doctor
from ._remote_commands import _run_edit, _run_remote_command, _run_sh, _run_script, _run_terminal, _run_interactive
from ._file_commands import _run_files
from ._job_commands import _run_jobs

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

__all__ = [name for name in globals() if not name.startswith("__")]
