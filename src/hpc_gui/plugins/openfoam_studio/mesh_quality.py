"""Mesh metadata + checkMesh interpretation (W65 MESH-005, G11).

Parses real ``checkMesh`` stdout; never fabricates quality metrics.
Missing or binary/unreadable mesh reports UNKNOWN, never PASS.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MeshQuality:
    cells: int | None
    points: int | None
    max_non_ortho: float | None
    max_skewness: float | None
    failed: bool
    raw_excerpt: str


def parse_check_mesh(stdout: str) -> MeshQuality:
    cells = _find_int(stdout, r"cells:\s+(\d+)")
    points = _find_int(stdout, r"points:\s+(\d+)")
    non_ortho = _find_float(stdout, r"Max non-orthogonality[^\d]*([\d.]+)")
    skew = _find_float(stdout, r"Max skewness[^\d]*([\d.]+)")
    failed = "Failed" in stdout and "checkMesh" in stdout or "***" in stdout and "Failed" in stdout
    failed = bool(re.search(r"mesh\s+(check\s+)?failed|Failed \d+ mesh checks", stdout, re.I))
    return MeshQuality(cells, points, non_ortho, skew, failed, stdout[:2000])


def _find_int(text: str, pattern: str) -> int | None:
    match = re.search(pattern, text)
    return int(match.group(1)) if match else None


def _find_float(text: str, pattern: str) -> float | None:
    match = re.search(pattern, text)
    try:
        return float(match.group(1)) if match else None
    except ValueError:
        return None


def quality_verdict(quality: MeshQuality) -> str:
    if quality.cells is None:
        return "UNKNOWN-no-data"
    if quality.failed:
        return "FAIL"
    if quality.max_non_ortho is not None and quality.max_non_ortho > 70:
        return "FAIL-nonOrtho"
    return "PASS-parsed"
