"""Selection state: edition/version/solver/profile gating (W65 UI-012, G34)."""

from __future__ import annotations

from dataclasses import dataclass

from hpc_gui.openfoam_core.release_support import (
    CASE_STUDIO_EDITION,
    release_profile,
    supported_releases,
)

EDITIONS = {CASE_STUDIO_EDITION: supported_releases()}
VERSIONS = {release: release_profile(release)["status"] for release in EDITIONS[CASE_STUDIO_EDITION]}
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
        raise ValueError(f"version '{version}' unavailable for {edition}")
    if solver not in release_profile(version)["solvers"]:
        raise ValueError(f"solver '{solver}' is not enabled for {version}")
    if mode not in MODES:
        raise ValueError(f"mode '{mode}' invalid")
    return Selection(edition, version, solver, mode, profile)
