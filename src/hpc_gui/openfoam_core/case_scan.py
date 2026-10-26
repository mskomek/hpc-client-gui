"""Case layout scanning and filename classification (W65 BASE-001)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath


SYSTEM_FILES = {"controlDict", "fvSchemes", "fvSolution", "decomposeParDict"}
CONSTANT_FILES = {"transportProperties", "thermophysicalProperties", "turbulenceProperties",
                  "g", "regionProperties", "polyMesh"}
FIELD_DIRS = {"0", "0.orig"}


def classify_case_path(relpath: str) -> str:
    parts = PurePosixPath(relpath.replace("\\", "/")).parts
    if not parts:
        return "unknown"
    if parts[0] == "system" and len(parts) == 2:
        return "system" if parts[1] in SYSTEM_FILES or parts[1].endswith("Dict") else "system-extra"
    if parts[0] == "constant":
        return "constant"
    if parts[0] in FIELD_DIRS:
        return "field"
    if parts[0] == "0" and len(parts) > 1:
        return "field"
    if parts[0] == "Allrun" or (len(parts) == 1 and parts[0].startswith("All")):
        return "script-untrusted"
    if relpath.endswith((".stl", ".STL", ".obj", ".OBJ", ".vtk", ".VTK")):
        return "geometry"
    return "unknown"


@dataclass
class CaseScan:
    root: str
    files: list[str] = field(default_factory=list)
    classes: dict[str, str] = field(default_factory=dict)
    has_system: bool = False
    has_constant: bool = False
    has_fields: bool = False
    has_polymesh: bool = False


def scan_case(root: str, relpaths: list[str]) -> CaseScan:
    scan = CaseScan(root=root)
    for rel in relpaths:
        scan.files.append(rel)
        cls = classify_case_path(rel)
        scan.classes[rel] = cls
        if cls in ("system", "system-extra"):
            scan.has_system = True
        if cls == "constant":
            scan.has_constant = True
        if cls == "field":
            scan.has_fields = True
        if "polyMesh" in rel.replace("\\", "/"):
            scan.has_polymesh = True
    return scan
