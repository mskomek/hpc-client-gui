"""Mesh converters + multi-region helpers (W65 MESH-005, G12/G13)."""

from __future__ import annotations

import os
import shutil

VERIFIED_CONVERTERS = {
    "gmshToFoam": (".msh",),
    "fluentMeshToFoam": (".msh", ".cas"),
    "ideasUnvToFoam": (".unv",),
    "foamToVTK": (),
}

REGION_REQUIRED = ("regionProperties",)


def converter_for(filename: str) -> str:
    suffix = os.path.splitext(filename)[1].lower()
    for tool, suffixes in VERIFIED_CONVERTERS.items():
        if suffix in suffixes and tool != "foamToVTK":
            return tool
    raise ValueError(f"no verified v2312 converter for '{filename}' (unsupported format)")


def converter_available(tool: str) -> bool:
    return shutil.which(tool) is not None


def converter_argv(tool: str, mesh_file: str, case_dir: str = ".") -> list[str]:
    if tool not in VERIFIED_CONVERTERS or tool == "foamToVTK":
        raise ValueError(f"converter '{tool}' is not a verified import converter")
    expected = converter_for(mesh_file)  # validates suffix
    if tool != expected and not (tool == "fluentMeshToFoam" and mesh_file.endswith(".msh")):
        raise ValueError(f"converter '{tool}' does not accept '{mesh_file}'")
    return [tool, "-case", case_dir, mesh_file]


def region_properties_dict(fluid_regions: list[str], solid_regions: list[str]) -> str:
    if not fluid_regions:
        raise ValueError("CHT requires at least one fluid region")
    fluids = " ".join(f'"{r}"' for r in fluid_regions)
    solids = " ".join(f'"{r}"' for r in solid_regions)
    return (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n    class dictionary;\n    object regionProperties;\n}\n"
        f"regions\n(\n    fluid ( {fluids} )\n    solid ( {solids} )\n);\n"
    )


def topo_set_dict(actions: list[dict]) -> str:
    """Typed system/topoSetDict from explicit zone actions (G12 subset).

    Each action: {"name", "type": "cellSet|faceSet|cellZoneSet",
    "source": "boxToCell|...", "params": {...}}. Unknown action types are
    rejected; nothing is auto-guessed.
    """
    allowed = {"cellSet", "faceSet", "cellZoneSet", "faceZoneSet"}
    if not actions:
        raise ValueError("topoSet requires at least one action")
    blocks = []
    for act in actions:
        name, kind = act.get("name", ""), act.get("type", "")
        if not name or any(c in name for c in " \t\n;|&$`\"'"):
            raise ValueError(f"unsafe topoSet name '{name}'")
        if kind not in allowed:
            raise ValueError(f"topoSet type '{kind}' is RAW-ADVANCED only")
        source = act.get("source", "boxToCell")
        blocks.append(f"    {{\n        name {name};\n        type {kind};\n"
                      f"        action new;\n        source {source};\n    }}\n")
    return ("FoamFile\n{\n    version 2.0;\n    format ascii;\n    class dictionary;\n"
            "    object topoSetDict;\n}\nactions\n(\n" + "".join(blocks) + ");\n")


def zone_argv(op: str, case_dir: str = ".", extra: tuple[str, ...] = ()) -> list[str]:
    """Argv for zone/split mesh ops. Destructive ops always carry -overwrite
    explicitly so the compiler guard can require confirmation."""
    if op == "topoSet":
        return ["topoSet", "-case", case_dir]
    if op == "splitMeshRegions":
        return ["splitMeshRegions", "-case", case_dir, "-overwrite", *extra]
    if op == "createPatch":
        return ["createPatch", "-case", case_dir, "-overwrite", *extra]
    raise ValueError(f"zone op '{op}' is RAW-ADVANCED only (no typed argv)")


def zone_rollback_note(op: str) -> str:
    return (f"{op}: restore constant/polyMesh from pre-op backup before retry; "
            "zone ops are not auto-rolled-back")
