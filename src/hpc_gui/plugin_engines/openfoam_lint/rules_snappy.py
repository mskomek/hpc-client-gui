"""Static completeness checks for snappyHexMeshDict (W65 MESH-005/LINT-013).

Only documented top-level switches and their required control dictionaries are
inspected; no geometry is read, no mesh is generated and no executable runs.
"""
from __future__ import annotations

from hpc_gui.openfoam_core import Diagnostic, ParsedDictionary, SOURCE_DOCS

_SWITCHES = {
    "castellatedMesh": "castellatedMeshControls",
    "snap": "snapControls",
    "addLayers": "addLayersControls",
}


def _switch(parsed: ParsedDictionary, key: str) -> bool | None:
    """True/False for a static switch, None when it cannot be judged."""
    entries = parsed.find(key)
    if not entries:
        return True
    if len(entries) != 1 or entries[0].dynamic:
        return None
    value = entries[0].value.strip().strip('"').lower()
    if value in {"true", "on", "yes", "1"}:
        return True
    if value in {"false", "off", "no", "0"}:
        return False
    return None


def _has_dictionary(parsed: ParsedDictionary, key: str) -> bool:
    entries = parsed.find(key)
    if len(entries) != 1:
        return False
    entry = entries[0]
    return bool(entry.is_dictionary or (entry.value or "").strip().startswith("{"))


def _has_include(parsed: ParsedDictionary) -> bool:
    return any(
        token.kind == "directive" and token.value in {"#include", "#includeEtc"}
        for token in parsed.tokens
    )


def lint_snappy_dict(files: dict[str, ParsedDictionary]) -> tuple[Diagnostic, ...]:
    """Report missing snappy controls for enabled stages."""
    findings: list[Diagnostic] = []
    for path, parsed in sorted(files.items()):
        if not path.endswith("snappyHexMeshDict"):
            continue
        required = ["meshQualityControls"]
        for switch, control in _SWITCHES.items():
            enabled = _switch(parsed, switch)
            if enabled is None:
                continue
            if enabled:
                required.append(control)
        missing = [name for name in required if not _has_dictionary(parsed, name)]
        if not missing:
            continue
        note = ""
        if _has_include(parsed):
            note = " Includes are not expanded by static lint, so an included block cannot be confirmed."
        findings.append(Diagnostic(
            "OF-MESH-010", "warning", "structural", path, 1, 1,
            f"snappyHexMeshDict is missing required controls: {', '.join(missing)}.{note}",
            "Add the missing control dictionaries for every enabled snappy stage, "
            "or disable that stage explicitly.",
            SOURCE_DOCS, verification_level="static",
        ))
    return tuple(findings)
