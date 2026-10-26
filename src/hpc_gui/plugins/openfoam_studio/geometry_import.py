"""Geometry import: STL/OBJ/VTK tri-surface metadata (W65 GEOM-004, G06)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

SUPPORTED_SUFFIXES = (".stl", ".obj", ".vtk")
MAX_BYTES = 200 * 1024 * 1024


@dataclass(frozen=True)
class SurfaceInfo:
    filename: str
    fmt: str
    size_bytes: int
    bounds: tuple | None
    facet_count: int | None
    warnings: tuple


def inspect_surface(path: str, size_bytes: int, head: bytes) -> SurfaceInfo:
    suffix = os.path.splitext(path)[1].lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"unsupported geometry format '{suffix}' (supported: STL/OBJ/VTK)")
    if size_bytes <= 0:
        raise ValueError("missing geometry file (zero size or absent)")
    if size_bytes > MAX_BYTES:
        raise ValueError("geometry file exceeds 200 MiB safety limit")
    warnings: list[str] = []
    bounds = None
    facets = None
    try:
        text = head.decode("utf-8", errors="ignore")
    except Exception:
        text = ""
    if suffix == ".stl" and text.lstrip().lower().startswith("solid"):
        verts = re.findall(r"vertex\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)", text[:65536])
        facets = text[:65536].count("facet normal")
        if verts:
            xs = [float(v[0]) for v in verts]; ys = [float(v[1]) for v in verts]; zs = [float(v[2]) for v in verts]
            bounds = ((min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs)))
        if facets == 0:
            warnings.append("no facets parsed in ASCII STL head; file may be binary or corrupt")
    elif suffix == ".obj":
        verts = re.findall(r"^v\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)", text[:65536], re.M)
        if verts:
            xs = [float(v[0]) for v in verts]; ys = [float(v[1]) for v in verts]; zs = [float(v[2]) for v in verts]
            bounds = ((min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs)))
    if bounds is None:
        warnings.append("bounds UNKNOWN from head sample; full import will re-measure")
    fmt = {"stl": "STL", "obj": "OBJ", "vtk": "VTK"}[suffix[1:]]
    return SurfaceInfo(os.path.basename(path), fmt, size_bytes, bounds, facets, tuple(warnings))


def tri_surface_dict_entry(stl_name: str) -> str:
    safe = stl_name.replace('"', "")
    return (f"{safe}\n{{\n    type triSurfaceMesh;\n    file \"{safe}\";\n}}\n")
