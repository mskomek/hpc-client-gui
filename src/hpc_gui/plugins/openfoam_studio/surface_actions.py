"""Surface quality wizard + feature-extraction schemas (W65 GEOM-004, G07).

Typed subset: triangulated-surface intake metadata, open/non-manifold/
overlap warnings, and a v2312-backed ``surfaceFeatureExtractDict`` writer.
Anything outside the typed checks stays RAW-ADVANCED: reported, never
silently claimed.
"""

from __future__ import annotations


def surface_quality_report(*, facet_count: int | None, bounds: tuple | None,
                           size_bytes: int, warnings: tuple[str, ...] = ()) -> dict:
    """Evaluate intake metadata; MISSING/UNKNOWN, never fabricated.

    Raises ``ValueError`` on oversize/empty inputs (negative fixtures).
    """
    if size_bytes <= 0:
        raise ValueError("surface intake is empty; refusing EMPTY success")
    if size_bytes > 200 * 1024 * 1024:
        raise ValueError("surface exceeds 200 MiB intake cap; use external decimation")
    if facet_count is not None and facet_count <= 0:
        raise ValueError("facet count must be positive")
    quality = "UNKNOWN" if facet_count is None else ("OK" if facet_count > 0 else "EMPTY")
    if bounds is None:
        quality = "UNKNOWN"
    return {"facets": facet_count if facet_count is not None else "MISSING",
            "bounds": bounds if bounds is not None else "MISSING",
            "size_bytes": size_bytes,
            "quality": quality,
            "warnings": list(warnings),
            "provenance": "surface-wizard:w65r2"}


def feature_extract_dict(surfaces: list[str], *, included_angle: float = 150.0,
                         subset: str | None = None) -> str:
    """Render a typed ``surfaceFeatureExtractDict`` for named surfaces."""
    if not surfaces:
        raise ValueError("feature extraction requires at least one surface")
    if not 0.0 < included_angle <= 180.0:
        raise ValueError("includedAngle must be within (0, 180]")
    blocks = []
    for name in surfaces:
        if not name or any(c in name for c in " \t\n;|&$`\"'"):
            raise ValueError(f"unsafe surface name '{name}'")
        entry = (f"    {name}\n    {{\n        extractionMethod extractFromSurface;\n"
                 f"        includedAngle {included_angle:g};\n")
        if subset:
            entry += f"        subset {subset};\n"
        entry += "    }\n"
        blocks.append(entry)
    return ("FoamFile\n{\n    version 2.0;\n    format ascii;\n"
            "    class dictionary;\n    object surfaceFeatureExtractDict;\n}\n"
            + "".join(blocks))


def feature_extract_argv(surface_file: str, case_dir: str = ".") -> list[str]:
    if not surface_file.lower().endswith((".stl", ".obj", ".vtp", ".vtk")):
        raise ValueError(f"unsupported surface '{surface_file}' for feature extraction")
    return ["surfaceFeatureExtract", "-case", case_dir]
