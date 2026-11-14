"""Compatibility facade: the gates live in :mod:`hpc_gui.openfoam_core.shell_safety`."""

from __future__ import annotations

from hpc_gui.openfoam_core.shell_safety import (  # noqa: F401
    ALLOWED_EXECUTABLES,
    SHELL_META,
    ScriptTrust,
    UntrustedArgvError,
    UntrustedScriptError,
    allowlist_name,
    assert_argv_allowed,
    assert_argv_safe,
    executable_name,
    include_is_safe,
    quote_argv,
    render_exec_line,
)

__all__ = [
    "ALLOWED_EXECUTABLES",
    "SHELL_META",
    "ScriptTrust",
    "UntrustedArgvError",
    "UntrustedScriptError",
    "allowlist_name",
    "assert_argv_allowed",
    "assert_argv_safe",
    "executable_name",
    "include_is_safe",
    "quote_argv",
    "render_exec_line",
]

