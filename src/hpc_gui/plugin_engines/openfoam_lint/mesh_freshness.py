"""Static geometry-versus-mesh freshness check (W65 LINT-013).
Only file metadata is read: no mesh, geometry or solver content is decoded and
nothing is executed. The check is local-only because it needs modification
times that the read-only text lint path does not carry.
"""
from __future__ import annotations

import os
from pathlib import Path

from hpc_gui.openfoam_core import Diagnostic, SOURCE_DOCS

MAX_SURFACE_FILES = 64
MAX_SURFACE_FINDINGS = 8
SURFACE_SUFFIXES = {".stl", ".obj", ".tri"}


def _mtime(path: Path) -> float | None:
    try:
        if path.is_symlink() or not path.is_file():
            return None
        return path.stat().st_mtime
    except OSError:
        return None


def stale_mesh_findings(root: Path) -> tuple[Diagnostic, ...]:
    """Report surface geometry newer than the generated mesh points file."""
    mesh_points = root / "constant" / "polyMesh" / "points"
    mesh_time = _mtime(mesh_points)
    if mesh_time is None:
        return ()
    surface_dir = root / "constant" / "triSurface"
    surfaces: list[Path] = []
    truncated = False
    try:
        with os.scandir(surface_dir) as entries:
            for entry in entries:
                if len(surfaces) >= MAX_SURFACE_FILES:
                    truncated = True
                    break
                if Path(entry.name).suffix.lower() not in SURFACE_SUFFIXES:
                    continue
                surfaces.append(surface_dir / entry.name)
    except OSError:
        return ()
    findings: list[Diagnostic] = []
    for entry in sorted(surfaces, key=lambda item: item.name):
        if len(findings) >= MAX_SURFACE_FINDINGS:
            break
        surface_time = _mtime(entry)
        if surface_time is None or surface_time <= mesh_time:
            continue
        findings.append(Diagnostic(
            "OF-CROSS-006", "info", "contextual",
            f"constant/triSurface/{entry.name}", 1, 1,
            f"Surface {entry.name!r} is newer than constant/polyMesh/points; "
            "the mesh may have been generated from older geometry.",
            "Regenerate the mesh from the current surface, or confirm the points file is "
            "intentionally older than the geometry.",
            SOURCE_DOCS, verification_level="contextual",
        ))
    if truncated:
        findings.append(Diagnostic(
            "OF-CROSS-006", "info", "contextual", "constant/triSurface", 1, 1,
            f"More than {MAX_SURFACE_FILES} surface files were found; the newer-than-mesh "
            "comparison covered only the first batch.",
            "Reduce the geometry set or compare the remaining surfaces manually.",
            SOURCE_DOCS, verification_level="contextual",
        ))
    return tuple(findings)
