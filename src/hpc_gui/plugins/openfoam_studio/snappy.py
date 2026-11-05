"""Typed snappyHexMesh authoring (W65 MESH-005, G10)."""

from __future__ import annotations

from hpc_gui.plugins.openfoam_studio.command_schemas import validate


def render_snappy_dict(*, max_global_cells: int, castellated: bool = True,
                       snap: bool = True, add_layers: bool = False,
                       n_layers: int = 0, expansion_ratio: float = 1.2,
                       refinement_surfaces: list[str] | None = None) -> str:
    params = validate("snappyHexMesh", {
        "castellatedMesh": castellated, "snap": snap, "addLayers": add_layers,
        "maxGlobalCells": max_global_cells, "nLayers": n_layers,
        "expansionRatio": expansion_ratio})
    if max_global_cells > 50_000_000:
        raise ValueError("maxGlobalCells exceeds 50M review threshold; split the mesh or confirm capacity")
    surfaces = refinement_surfaces or []
    surf_block = "\n".join(f"        {s} {{ level (2 2); }}" for s in surfaces)
    return (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n    class dictionary;\n    object snappyHexMeshDict;\n}\n"
        f"castellatedMeshControls\n{{\n    maxGlobalCells {params['maxGlobalCells']};\n"
        f"    minRefinementCells 10;\n    nCellsBetweenLevels 3;\n    refinementSurfaces\n    {{\n{surf_block}\n    }}\n}}\n"
        f"snapControls {{ nSmoothPatch 3; tolerance 2.0; nSolveIter 30; }}\n"
        f"addLayersControls {{ nSurfaceLayers {params['nLayers']}; expansionRatio {params['expansionRatio']}; }}\n"
        f"meshQualityControls {{ maxNonOrtho 65; maxSkewness 4; }}\n"
        f"castellatedMesh {'on' if params['castellatedMesh'] else 'off'};\n"
        f"snap {'on' if params['snap'] else 'off'};\n"
        f"addLayers {'on' if params['addLayers'] else 'off'};\n"
    )
