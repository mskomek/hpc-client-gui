"""Release-specific inventory facade for the Case Studio catalog."""

from __future__ import annotations

from hpc_gui.openfoam_core.release_support import release_profile

from .catalog_inventory import inventory as inventory_v2312


def inventory_for_release(release: str) -> tuple[dict, ...]:
    """Return source-backed inventory rows for the requested supported release.

    v1912 intentionally exposes only its three source- and runtime-verified
    commands. It does not inherit the larger v2312 inventory.
    """
    profile = release_profile(release)
    if release == "v2312":
        return tuple(inventory_v2312())
    source_paths = profile["source_paths"]
    return tuple({
        "uid": f"of1912:{name}",
        "edition": "esi",
        "release": release,
        "command_name": name,
        "kind": "solver" if name == "simpleFoam" else "utility",
        "availability": "ACTIVE-TYPED",
        "proof_level": "RUNTIME-EXECUTED",
        "source_revision": profile["source_tag"],
        "source_commit": profile["source_revision"],
        "source_path": source_paths[name],
        "reason": "OpenCFD source tag and Kole Ubuntu-Test runtime verified; limited profile",
    } for name in profile["commands"])


def coverage_for_release(release: str) -> dict:
    """Summarize only the declared profile, without implying full release coverage."""
    profile = release_profile(release)
    rows = inventory_for_release(release)
    return {
        "release": release,
        "profile": profile["feature_level"],
        "declared_commands": len(profile["commands"]),
        "inventory_rows": len(rows),
        "solvers": profile["solvers"],
        "truba_module": profile["truba_module"],
    }
