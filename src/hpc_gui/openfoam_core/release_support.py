"""Explicit OpenFOAM.com release profiles supported by the host tools.

Profiles describe the verified feature boundary for each release. They are
data only: adding a version never enables an unverified executable or site
module implicitly.
"""

from __future__ import annotations


OPENFOAM_EDITION = "OpenFOAM.com / ESI"
CASE_STUDIO_EDITION = "OpenFOAM.com / ESI (OpenCFD)"

_V2312_COMMANDS = (
    "blockMesh", "checkMesh", "decomposePar", "simpleFoam",
    "reconstructPar", "postProcess",
)

_RELEASES = {
    "v2312": {
        "status": "active",
        "feature_level": "source-catalog",
        "commands": _V2312_COMMANDS,
        "solvers": ("icoFoam", "simpleFoam", "pimpleFoam",
                    "chtMultiRegionSimpleFoam", "buoyantSimpleFoam",
                    "rhoSimpleFoam", "interFoam"),
        "typed_commands": (
            "blockMesh", "checkMesh", "surfaceFeatureExtract", "snappyHexMesh",
            "decomposePar", "reconstructPar", "splitMeshRegions", "setFields",
            "simpleFoam", "pimpleFoam", "icoFoam", "chtMultiRegionSimpleFoam",
            "postProcess", "foamToVTK", "probes", "fieldAverage", "forces",
            "forceCoeffs", "yPlus", "wallShearStress",
        ),
        "catalog_file": "engine/openfoam_studio/data/command_catalog.json",
        "truba_module": "apps/openfoam/v2312-2025",
        "source_tag": "OpenFOAM-v2312",
        "source_revision": "",
    },
    "v1912": {
        "status": "limited",
        "feature_level": "runtime-verified-subset",
        "commands": ("blockMesh", "checkMesh", "simpleFoam"),
        "solvers": ("simpleFoam",),
        "typed_commands": ("blockMesh", "checkMesh", "simpleFoam"),
        "catalog_file": "engine/openfoam_studio/data/command_catalog_v1912.json",
        "truba_module": None,
        "source_tag": "OpenFOAM-v1912.200626",
        "source_revision": "51dd8f1c633dda9a38e974bded29f0c772f42fe9",
        "source_paths": {
            "blockMesh": "applications/utilities/mesh/generation/blockMesh",
            "checkMesh": "applications/utilities/mesh/manipulation/checkMesh",
            "simpleFoam": "applications/solvers/incompressible/simpleFoam",
        },
        "runtime_package": "openfoam 1912.200626-2build3",
        "runtime_case": "incompressible/simpleFoam/pitzDaily-core-only",
        "runtime_evidence": "Kole Ubuntu-Test W65 v1912 test, 2026-10-27",
    },
}


def supported_releases() -> tuple[str, ...]:
    """Return releases in their stable UI order (default first)."""
    return tuple(_RELEASES)


def release_profile(release: str) -> dict:
    """Return a defensive copy of one known release profile."""
    if not isinstance(release, str) or release not in _RELEASES:
        raise ValueError(f"unsupported OpenFOAM.com release: {release!r}")
    profile = dict(_RELEASES[release])
    if "source_paths" in profile:
        profile["source_paths"] = dict(profile["source_paths"])
    return profile


def linter_supports_release(release: str) -> bool:
    """Static linter rules support the common dictionary subset in both releases."""
    return isinstance(release, str) and release in _RELEASES
