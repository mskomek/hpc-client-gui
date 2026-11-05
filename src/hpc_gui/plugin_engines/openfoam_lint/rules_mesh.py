"""Contextual checks that require actual constant/polyMesh metadata."""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Mapping

from hpc_gui.openfoam_core import (
    Diagnostic,
    ParsedDictionary,
    SOURCE_DOCS,
    parse_mesh_boundary_names,
)


_REGEX_MARKERS = frozenset(".*+?[]()|{}^$\\")


def _mesh_region(path: str) -> tuple[str, ...]:
    parts = PurePosixPath(path).parts
    try:
        boundary_index = parts.index("polyMesh")
    except ValueError:
        return ()
    return parts[1:boundary_index]


def _field_region(path: str) -> tuple[str, ...] | None:
    parts = PurePosixPath(path).parts
    if len(parts) < 2 or parts[0] not in {"0", "0.orig"}:
        return None
    return parts[1:-1]


def lint_mesh_patch_consistency(
    fields: Mapping[str, ParsedDictionary],
    mesh_sources: Mapping[str, str],
) -> tuple[Diagnostic, ...]:
    """Compare literal field patches only against readable mesh boundary files."""
    findings: list[Diagnostic] = []
    meshes: dict[tuple[str, ...], list[tuple[str, frozenset[str]]]] = {}
    for path, source in mesh_sources.items():
        names = parse_mesh_boundary_names(source)
        if names is None:
            findings.append(Diagnostic(
                "OF-MESH-002", "info", "contextual", path, 1, 1,
                "Mesh boundary metadata is not an unambiguous static ASCII patch list; field/mesh patch coverage was not checked.",
                "Inspect the mesh with the matching OpenFOAM edition; binary, included, dynamic, or malformed metadata is not interpreted.",
                SOURCE_DOCS, verification_level="contextual",
            ))
            continue
        meshes.setdefault(_mesh_region(path), []).append((path, frozenset(names)))

    for path, parsed in fields.items():
        region = _field_region(path)
        if region is None:
            continue
        candidates = meshes.get(region, [])
        if len(candidates) != 1:
            continue
        mesh_path, mesh_patches = candidates[0]
        boundary_blocks = parsed.find("boundaryField", scope=())
        if len(boundary_blocks) != 1 or not boundary_blocks[0].is_dictionary:
            continue
        if any(token.kind == "directive" for token in parsed.tokens):
            continue
        patches = [
            entry for entry in parsed.entries
            if entry.is_dictionary and entry.scope == ("boundaryField",)
        ]
        names = [entry.key for entry in patches]
        if len(names) != len(set(names)) or any(
            any(marker in name for marker in _REGEX_MARKERS) for name in names
        ):
            continue
        field_patches = set(names)
        for name in sorted(mesh_patches - field_patches):
            block = boundary_blocks[0]
            findings.append(Diagnostic(
                "OF-MESH-001", "warning", "contextual", path, block.line, block.column,
                f"Mesh patch {name!r} has no matching field boundaryField entry.",
                "Add the field condition for this mesh patch, or review region and include usage manually.",
                SOURCE_DOCS, verification_level="contextual",
            ))
        for name in sorted(field_patches - mesh_patches):
            patch = next(entry for entry in patches if entry.key == name)
            findings.append(Diagnostic(
                "OF-MESH-001", "warning", "contextual", path, patch.line, patch.column,
                f"Field patch {name!r} is absent from the matching constant mesh boundary file {mesh_path!r}.",
                "Check the mesh patch name and the selected region; this comparison uses only the discovered constant mesh metadata.",
                SOURCE_DOCS, verification_level="contextual",
            ))
    return tuple(findings)
