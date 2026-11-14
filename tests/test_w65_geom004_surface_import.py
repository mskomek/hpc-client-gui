"""W65 GEOM-004: live inspection of a real ESI v2312 tri-surface."""

from __future__ import annotations

from pathlib import Path

import pytest

from hpc_gui.plugins.openfoam_studio.geometry_import import inspect_surface

FIXTURES = Path(__file__).parent / "fixtures"
STL = FIXTURES / "geom004_sphere_with_hole.stl"


def test_inspect_real_v2312_ascii_stl():
    data = STL.read_bytes()
    info = inspect_surface("sphere_with_hole.stl", len(data), data[:65536])
    assert info.fmt == "STL"
    assert info.size_bytes == 53799
    assert info.bounds == ((0.0, 3.0), (0.0, 3.0), (0.0, 3.0))
    assert info.facet_count == 287
    assert info.warnings == ()


def test_truncated_head_reports_only_what_it_contains():
    data = STL.read_bytes()
    info = inspect_surface("sphere_with_hole.stl", len(data), data[:4096])
    assert info.size_bytes == 53799
    assert info.facet_count == 23
    (x0, x1), _, _ = info.bounds
    assert x0 > 0.0 and x1 < 3.0


def test_head_cut_before_any_vertex_reports_unknown_bounds():
    data = STL.read_bytes()
    info = inspect_surface("sphere_with_hole.stl", len(data), data[:40])
    assert info.bounds is None
    assert any("bounds UNKNOWN" in w for w in info.warnings)


def test_binary_stl_head_warns_instead_of_inventing_bounds():
    binary = bytes(range(84)) + b"\x00" * 400
    info = inspect_surface("binary.stl", 200000, binary)
    assert info.fmt == "STL"
    assert info.bounds is None
    assert any("bounds UNKNOWN" in w for w in info.warnings)
    assert info.facet_count is None


def test_unsupported_suffix_and_zero_size_are_refused():
    with pytest.raises(ValueError):
        inspect_surface("part.step", 100, b"ISO-10303-21;")
    with pytest.raises(ValueError):
        inspect_surface("part.stl", 0, b"")


def test_oversize_geometry_is_refused():
    with pytest.raises(ValueError):
        inspect_surface("huge.stl", 201 * 1024 * 1024, b"solid x")
