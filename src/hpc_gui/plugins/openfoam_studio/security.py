"""Security gates: includes, symlinks, shell argv (W65 SAFE-016, G43)."""

from __future__ import annotations

import shlex
from pathlib import Path, PurePosixPath, PureWindowsPath

SHELL_META = (";", "&", "|", "$", "`", ">", "<", "\n", "\r")


def include_is_safe(include_target: str, case_root: str) -> bool:
    normalized = include_target.replace("\\", "/")
    target = PurePosixPath(normalized)
    windows_target = PureWindowsPath(include_target)
    if target.is_absolute() or windows_target.drive or windows_target.root:
        return False
    if ".." in target.parts or not target.parts:
        return False
    root = Path(case_root)
    try:
        resolved_root = root.resolve(strict=False)
        resolved_target = root.joinpath(*target.parts).resolve(strict=False)
        resolved_target.relative_to(resolved_root)
        return True
    except (OSError, RuntimeError, ValueError):
        return False


def assert_argv_safe(argv: list[str]) -> None:
    for token in argv:
        if any(m in token for m in SHELL_META):
            raise ValueError(f"refusing argv token with shell metacharacter: {token!r}")


def quote_argv(argv: list[str]) -> str:
    assert_argv_safe(argv)
    return " ".join(shlex.quote(a) for a in argv)
