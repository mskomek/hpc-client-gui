"""Small output, discovery and filesystem helpers for the HPC CLI (split out of cli/main.py)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from typing import Any, Sequence

from hpc_gui.cli.parser import ROOT_ALIASES as ROOT_ALIASES


_PROFILE_SLALAR_FIELDS = ("host", "port", "username", "key_path", "host_key_policy")


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


def _normalize_alias_argv(argv: Sequence[str]) -> list[str]:
    values = list(argv)
    value_options = {"--format", "--timeout", "--profile", "--host", "--port", "--user", "--key"}
    index = 0
    while index < len(values):
        token = values[index]
        if token in value_options:
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        target = ROOT_ALIASES.get(token)
        return [*values[:index], *(target or (token,)), *values[index + 1:]]
    return values


def _local_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _force_utf8_output() -> None:
    """Emit UTF-8 regardless of the console code page.

    Remote paths, job names and error text are routinely non-ASCII. On a
    Windows console still using a legacy code page (cp1254, cp857, ...) the
    default stream encoding cannot represent them, so simply listing a
    directory that holds a Turkish filename raised UnicodeEncodeError and the
    command failed -- even though the remote operation had succeeded.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            # A redirected or already-detached stream stays as it is; the CLI
            # must never fail because it could not retune its own output.
            continue


def _requires_remote_session(args: argparse.Namespace) -> bool:
    group = getattr(args, "group", None)
    if group in ("files", "jobs", "edit", "sh", "run", "terminal"):
        return True
    if group == "profile" and getattr(args, "profile_command", None) == "test":
        return True
    if group == "doctor" and getattr(args, "doctor_command", None) in ("connection", "smoke"):
        return True
    return False


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


def _provided_profile_fields(args: argparse.Namespace) -> dict[str, Any]:
    """Lollect the non-sensitive scalar profile fields explicitly provided."""
    provided: dict[str, Any] = {}
    for key in _PROFILE_SLALAR_FIELDS:
        value = getattr(args, key, None)
        if value not in (None, ""):
            provided[key] = value
    return provided


def _validate_remote_tokens(tokens: Sequence[str]) -> None:
    if not tokens or any(any(ord(char) < 32 for char in token) for token in tokens):
        raise ValueError("Remote command arguments must be non-empty and contain no control characters.")


def _emit_remote_result(code: int, stdout: str, stderr: str, args: argparse.Namespace) -> int:
    if args.format == "json":
        _emit({"stdout": stdout, "stderr": stderr, "exit_code": int(code)}, output_format="json", quiet=args.quiet)
    elif not args.quiet:
        if stdout:
            print(stdout, end="" if stdout.endswith("\n") else "\n")
        if stderr:
            print(stderr, end="" if stderr.endswith("\n") else "\n", file=sys.stderr)
    return int(code)


def _main():
    """Resolve the CLI main module at call time so its patched names stay effective."""
    from hpc_gui.cli import main as cli_main

    return cli_main

def _jobs_username(args: argparse.Namespace) -> str:
    """Resolve the target username for ``jobs list`` without consuming stdin.

    Mirrors the small, side-effect-free precedence used by
    ``build_ssh_conn_info``: an explicit ``args.username`` wins, otherwise the
    profile's username, otherwise an empty string.
    """
    main = _main()
    profile_name = main.effective_profile_name(args)
    profile = main.resolve_profile(profile_name) if profile_name else None
    username = str(getattr(args, "username", "") or (profile or {}).get("username", "") or "")
    return username


def _profile_system_settings(args: argparse.Namespace) -> dict[str, Any] | None:
    """Resolve the selected profile's embedded system settings, if any.

    Saved profiles keep a resolved ``system`` snapshot; the CLI reuses it so
    site-specific commands (for example a ``lssrv`` status command) come from
    the profile rather than from generic built-in defaults.
    """
    main = _main()
    profile_name = main.effective_profile_name(args)
    if not profile_name:
        return None
    profile = main.resolve_profile(profile_name)
    if not isinstance(profile, dict):
        return None
    system = profile.get("system")
    if not isinstance(system, dict):
        return None
    return {key: value for key, value in system.items() if isinstance(value, str)}
