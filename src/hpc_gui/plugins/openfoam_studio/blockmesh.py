"""Typed blockMesh authoring (W65 MESH-005, G09)."""

from __future__ import annotations

from hpc_gui.plugins.openfoam_studio.command_schemas import validate


def render_block_mesh_dict(nx: int, ny: int, nz: int, patches: list[str],
                           grading: str = "simpleGrading (1 1 1)") -> str:
    params = validate("blockMesh", {"nx": nx, "ny": ny, "nz": nz,
                                    "grading": grading, "patches": patches})
    if len(params["patches"]) == 0:
        raise ValueError("blockMesh requires at least one patch")
    patch_block = "\n".join(
        f"        {name}\n        {{\n            type patch;\n            faces\n            (\n            );\n        }}" for name in params["patches"])
    return (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n    class blockMeshDict;\n    object blockMeshDict;\n}\n"
        f"convertToMeters 1;\nvertices\n(\n);\nblocks\n(\n    hex (0 1 2 3 4 5 6 7)"
        f" ({params['nx']} {params['ny']} {params['nz']}) {params['grading']}\n);\n"
        f"edges\n(\n);\nboundary\n(\n{patch_block}\n);\n"
    )


def validate_topology(nx: int, ny: int, nz: int) -> None:
    for name, value in (("nx", nx), ("ny", ny), ("nz", nz)):
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(f"invalid block topology: {name}={value!r} (positive int required)")
