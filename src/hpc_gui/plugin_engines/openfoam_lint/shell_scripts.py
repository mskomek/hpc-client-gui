"""Presence-only warnings for untrusted case shell scripts.

Static lint never opens, evaluates, or runs Allrun/Allclean; the check below
only stats directory entries so a hostile script cannot execute while a case
is being inspected. Enumeration is cancellable, keeps memory bounded to the
matched names, skips reparse points, and fails loud when a listing is cut
short or a directory cannot be read part-way through.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from hpc_gui.openfoam_core import Diagnostic, SOURCE_DOCS
from hpc_gui.openfoam_core.cancellation import raise_if_cancelled

_SCRIPT_NAME = re.compile(r"^(?:allrun|allclean)(?:\.[a-z0-9_-]+)*$")
MAX_SCRIPT_WARNINGS = 8

#: Safety ceiling for one case-root listing. Real cases stay far below this,
#: so the reported set is deterministic for every ordinary case; a directory
#: that exceeds it reports the cut instead of returning a silent subset.
MAX_SCRIPT_SCAN_ENTRIES = 100_000


def _is_reparse_point(entry: os.DirEntry[str]) -> bool:
    """Treat symlinks, junctions and unknown entries as non-inspectable."""
    try:
        if entry.is_symlink():
            return True
        is_junction = getattr(entry, "is_junction", None)
        return bool(is_junction and is_junction())
    except OSError:
        return True


def _script_diagnostic(name: str, message: str, fix: str) -> Diagnostic:
    return Diagnostic(
        "OF-SEC-005", "warning", "certain", name, 1, 1, message, fix, SOURCE_DOCS,
        verification_level="contextual",
    )


def script_name_matches(name: str) -> bool:
    """True when a directory entry name is an Allrun/Allclean variant."""
    return bool(_SCRIPT_NAME.match(name.casefold()))


def script_diagnostics(names: list[str], *, truncated: bool = False) -> tuple[Diagnostic, ...]:
    """Ordered findings for already-collected script names."""
    ordered = sorted(names, key=lambda name: (name.casefold(), name))
    findings = [
        _script_diagnostic(
            name,
            f"{name} is an untrusted case shell script; static lint did not read or execute it.",
            f"Review {name} before running it, and run it only in a disposable case.",
        )
        for name in ordered[:MAX_SCRIPT_WARNINGS]
    ]
    if len(ordered) > MAX_SCRIPT_WARNINGS:
        findings.append(_script_diagnostic(
            "<scripts:cap>",
            f"{len(ordered)} untrusted case shell scripts were found; only the first "
            f"{MAX_SCRIPT_WARNINGS} are listed.",
            "Review every Allrun/Allclean script in the case root before running any of them.",
        ))
    if truncated:
        findings.append(_script_diagnostic(
            "<scripts:limit>",
            "The case root listing ended early; scripts beyond that point were not inspected.",
            "Re-run the lint, or select the case directories that contain the scripts directly.",
        ))
    return tuple(findings)


def shell_script_findings(root: Path, cancel_event=None) -> tuple[Diagnostic, ...]:
    """Report case-root shell scripts without reading their contents."""
    matches: list[str] = []
    scanned = 0
    listing_limited = False
    try:
        handle = os.scandir(root)
    except OSError:
        return ()
    with handle as entries:
        while True:
            try:
                entry = next(entries)
            except StopIteration:
                break
            except OSError:
                listing_limited = True
                break
            raise_if_cancelled(cancel_event)
            scanned += 1
            if scanned > MAX_SCRIPT_SCAN_ENTRIES:
                listing_limited = True
                break
            if not script_name_matches(entry.name):
                continue
            if _is_reparse_point(entry):
                continue
            try:
                if not entry.is_file():
                    continue
            except OSError:
                continue
            matches.append(entry.name)
    return script_diagnostics(matches, truncated=listing_limited)
