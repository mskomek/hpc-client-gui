"""External CAD converter gate (W65 GEOM-004, G08, P2 optional).

OpenFOAM v2312 has no native STEP/IGES kernel. Conversion requires an
explicitly installed external tool (FreeCAD/Gmsh/SALOME). Without one the
action is BLOCKED_EXTERNAL with an actionable explanation; never pretend
direct STEP support.
"""

from __future__ import annotations

import shutil

APPROVED_CONVERTERS = ("freecad", "freecadcmd", "gmsh", "salome")


class CadBlockedExternal(RuntimeError):
    pass


def probe_converters() -> dict[str, str | None]:
    return {name: shutil.which(name) for name in APPROVED_CONVERTERS}


def require_converter() -> str:
    found = probe_converters()
    for name, path in found.items():
        if path:
            return f"{name} ({path})"
    raise CadBlockedExternal(
        "BLOCKED_EXTERNAL: no approved CAD converter installed (FreeCAD/Gmsh/SALOME). "
        "Export STEP/IGES to STL/OBJ externally, then import the triangulated surface. "
        "STEP->mesh is NOT marked supported."
    )


def step_intake_status(step_path: str) -> dict:
    try:
        converter = require_converter()
        return {"path": step_path, "status": "CONVERTER-AVAILABLE", "converter": converter,
                "next": "convert to STL/OBJ with explicit units, then import as triangulated surface"}
    except CadBlockedExternal as exc:
        return {"path": step_path, "status": "BLOCKED_EXTERNAL", "reason": str(exc),
                "next": "manual converted-mesh import (J06 alternative path)"}
