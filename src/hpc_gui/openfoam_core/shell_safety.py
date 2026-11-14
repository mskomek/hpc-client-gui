"""Shell safety gates shared by the OpenFOAM branches (W65 SAFE-016, G43)."""

from __future__ import annotations

import hashlib
import shlex
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

SHELL_META = (";", "&", "|", "$", "`", ">", "<", "\n", "\r")

#: Executables a case-local command may name. Anything else is refused before
#: an argv list can become a shell line (W65 SAFE-016).
ALLOWED_EXECUTABLES = frozenset(
    {
        "blockMesh",
        "checkMesh",
        "decomposePar",
        "foamDictionary",
        "foamMultiRun",
        "icoFoam",
        "interFoam",
        "pimpleFoam",
        "pisoFoam",
        "postProcess",
        "potentialFoam",
        "reconstructPar",
        "reconstructParMesh",
        "setFields",
        "simpleFoam",
        "snappyHexMesh",
        "surfaceFeatureExtract",
        "bash",
    }
)


class UntrustedArgvError(ValueError):
    """An argv list names an executable or token the app will not run."""


class UntrustedScriptError(ValueError):
    """A case script was not approved, or its bytes changed after approval."""


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


def executable_name(argv: list[str]) -> str:
    """Return the bare executable name of an argv list (no directories)."""
    if not argv:
        raise UntrustedArgvError("refusing an empty argv")
    return PurePosixPath(str(argv[0]).replace("\\", "/")).name


def allowlist_name(argv: list[str]) -> str:
    """Return the allowlist key for argv[0], tolerating a resolved .exe name."""
    name = executable_name(argv)
    if name.lower().endswith(".exe"):
        return name[:-4]
    return name


def assert_argv_allowed(argv: list[str]) -> str:
    """Refuse anything outside the OpenFOAM allowlist, then the metacharacter gate."""
    name = allowlist_name(argv)
    if name not in ALLOWED_EXECUTABLES:
        raise UntrustedArgvError(f"refusing executable outside the allowlist: {name!r}")
    if name == "bash" and (len(argv) != 3 or argv[1] != "--"):
        raise UntrustedArgvError(
            "bash may only be invoked as 'bash -- <script>'; inline -c commands are refused"
        )
    assert_argv_safe(argv)
    return name


def quote_argv(argv: list[str]) -> str:
    assert_argv_safe(argv)
    return " ".join(shlex.quote(a) for a in argv)


def render_exec_line(argv: list[str]) -> str:
    """Quote an allowlisted argv list for a shell line; refuses otherwise."""
    assert_argv_allowed(argv)
    return " ".join(shlex.quote(a) for a in argv)


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value)


@dataclass(frozen=True)
class ScriptTrust:
    """Explicit approval of one script, bound to its SHA-256.

    A case script is untrusted input: it may only run when the operator approved
    exactly these bytes. The approval is the proof the app keeps (SAFE-016).
    """

    allrun_sha256: str
    approved: bool = False

    def __post_init__(self) -> None:
        if not _is_sha256(self.allrun_sha256):
            raise ValueError("script SHA-256 must be 64 lowercase hexadecimal characters")

    def verify(self, script_bytes: bytes) -> None:
        if not self.approved:
            raise UntrustedScriptError("script was not approved by the operator")
        digest = hashlib.sha256(script_bytes).hexdigest()
        if digest != self.allrun_sha256:
            raise UntrustedScriptError("script bytes changed after approval")

    def verify_path(self, script_path: str | Path) -> None:
        self.verify(Path(script_path).read_bytes())




