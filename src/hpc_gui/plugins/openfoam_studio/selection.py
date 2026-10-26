"""Selection state: edition/version/solver/profile gating (W65 UI-012, G34)."""

from __future__ import annotations

from dataclasses import dataclass

EDITIONS = {"OpenFOAM.com / ESI (OpenCFD)": ("v2312",)}
VERSIONS = {"v2312": "active"}
SOLVERS = ("icoFoam", "simpleFoam", "pimpleFoam", "chtMultiRegionSimpleFoam",
           "buoyantSimpleFoam", "rhoSimpleFoam", "interFoam")
MODES = ("serial", "parallel")


@dataclass(frozen=True)
class Selection:
    edition: str
    version: str
    solver: str
    mode: str
    profile: str


def select(edition: str, version: str, solver: str, mode: str, profile: str) -> Selection:
    if edition not in EDITIONS:
        raise ValueError(f"edition '{edition}' unsupported (disabled with reason)")
    if version not in EDITIONS[edition]:
        raise ValueError(f"version '{version}' unavailable for {edition}; only v2312 active")
    if solver not in SOLVERS:
        raise ValueError(f"solver '{solver}' not in typed selector (use RAW-ADVANCED path)")
    if mode not in MODES:
        raise ValueError(f"mode '{mode}' invalid")
    return Selection(edition, version, solver, mode, profile)
