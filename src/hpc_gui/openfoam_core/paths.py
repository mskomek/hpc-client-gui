"""Safe case-relative path contracts (W65 LINT-COMPAT).

Pure validation helpers with no filesystem access. Rejects absolute
paths, drive prefixes, backslashes, NUL/control characters, dot segments
and traversal so engines can fail closed before any read.
"""

from __future__ import annotations

from pathlib import PurePosixPath

_KNOWN_DICTIONARIES = frozenset({
    "controlDict", "fvSchemes", "fvSolution", "decomposeParDict",
    "blockMeshDict", "snappyHexMeshDict", "regionProperties",
    "transportProperties", "thermophysicalProperties",
    "turbulenceProperties", "fvOptions", "changeDictionaryDict",
    "topoSetDict", "surfaceFeatureExtractDict", "g",
})

_FIELD_ROOTS = frozenset({"0", "0.orig"})


def safe_relative_path(value: str) -> bool:
    """True only for a safe case-relative POSIX path."""
    if not isinstance(value, str) or not value:
        return False
    if "\\" in value or "\x00" in value:
        return False
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in value):
        return False
    if len(value) > 4096:
        return False
    normalized = value.replace("\\", "/")
    if normalized.startswith("/") or ".." in PurePosixPath(normalized).parts:
        return False
    if len(normalized) > 1 and normalized[1] == ":":
        return False
    parts = PurePosixPath(normalized).parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        return False
    if any(part.startswith(".") for part in parts):
        return False
    return True


def _leaf(relative: str) -> str:
    return str(relative).replace("\\", "/").rsplit("/", 1)[-1]


def is_dictionary_name(relative: str) -> bool:
    """True when a case-relative path names a static dictionary."""
    if not isinstance(relative, str) or not relative:
        return False
    normalized = relative.replace("\\", "/")
    parts = PurePosixPath(normalized).parts
    if not parts:
        return False
    leaf = parts[-1]
    if "polyMesh" in parts:
        return False
    if leaf in ("Allrun", "Allclean") or leaf.startswith("."):
        return False
    if normalized.endswith((".stl", ".STL", ".obj", ".OBJ", ".vtk", ".VTK")):
        return False
    if parts[0] in _FIELD_ROOTS:
        return True
    if leaf in _KNOWN_DICTIONARIES:
        return True
    if leaf.endswith("Dict") or leaf.endswith("Properties"):
        return True
    if parts[0] in ("system", "constant") and "." not in leaf:
        return True
    return False


def is_mesh_boundary_path(relative: str) -> bool:
    """True for ``constant/.../polyMesh/boundary`` metadata files."""
    if not isinstance(relative, str) or not relative:
        return False
    parts = PurePosixPath(relative.replace("\\", "/")).parts
    return "polyMesh" in parts and bool(parts) and parts[-1] == "boundary"
