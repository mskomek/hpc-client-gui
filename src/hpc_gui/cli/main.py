"""Command-line entrypoint and public compatibility facade."""

from __future__ import annotations

import platform
import sys
import argparse
import hashlib
import json
import os
import shlex
import subprocess
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
    CLIConnectionError as CLIConnectionError,
    CLISession as CLISession,
    build_ssh_conn_info,
    effective_profile_name,
    resolve_profile,
)
from hpc_gui.services.connection_diagnostics import run_connection_diagnostics
from hpc_gui.services.sftp_smoke import run_sftp_smoke
from hpc_gui.services.job_identity import is_valid_job_id
from hpc_gui.cli.files import (
    IF_EXISTS_CHOICES,
    download as download_files,
    upload as upload_files,
)
from hpc_gui.cli.jobs import emit_job_result, jobs_backend
from ._contracts import CLI_VERSION, ROOT_ALIASES
from ._shared import (
    _emit,
    _requires_remote_session,
    _safe_profile,
    _provided_profile_fields,
    _local_sha256,
    _validate_remote_tokens,
    _emit_remote_result,
    _normalize_alias_argv,
    _force_utf8_output,
    _jobs_username,
    _profile_system_settings,
    _is_valid_job_id,
)
from ._parser import _FullHelpArgumentParser, _parser, _walk_parser, _run_commands
from ._profile_commands import _run_profile
from ._doctor_commands import _run_doctor
from ._remote_commands import (
    _run_edit,
    _run_remote_command,
    _run_sh,
    _run_script,
    _run_terminal,
    _run_interactive,
    _shell_channel_is_active,
)
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
        return _run_interactive(args, run_cli)
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


__all__ = [
    "Any",
    "IF_EXISTS_CHOICES",
    "Path",
    "ROOT_ALIASES",
    "Sequence",
    "annotations",
    "app_data_dir",
    "argparse",
    "build_ssh_conn_info",
    "delete_profile",
    "download_files",
    "effective_profile_name",
    "emit_job_result",
    "hashlib",
    "is_valid_job_id",
    "jobs_backend",
    "json",
    "load_profiles",
    "os",
    "platform",
    "resolve_profile",
    "run_connection_diagnostics",
    "run_sftp_smoke",
    "shlex",
    "subprocess",
    "sys",
    "tempfile",
    "upload_files",
    "upsert_profile",
    "CLI_VERSION",
    "CLIConnectionError",
    "CLISession",
    "ExitCode",
    "emit_error",
    "get_cli_external_access_enabled",
    "_emit",
    "_emit_remote_result",
    "_force_utf8_output",
    "_is_valid_job_id",
    "_local_sha256",
    "_provided_profile_fields",
    "_profile_system_settings",
    "_safe_profile",
    "_jobs_username",
    "_normalize_alias_argv",
    "_FullHelpArgumentParser",
    "_run_remote_command",
    "_shell_channel_is_active",
    "_validate_remote_tokens",
    "_walk_parser",
    "_parser",
    "_requires_remote_session",
    "_run_commands",
    "_run_doctor",
    "_run_edit",
    "_run_files",
    "_run_interactive",
    "_run_jobs",
    "_run_profile",
    "_run_script",
    "_run_sh",
    "_run_terminal",
    "run_cli",
]
