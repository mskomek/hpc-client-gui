"""W65r2 F4: chart/report export + viewer handoff over real bytes (G29)."""
from __future__ import annotations

import pytest

from hpc_gui.plugins.openfoam_studio.monitor import parse_log
from hpc_gui.plugins.openfoam_studio.plot_export import (
    SeriesMeta,
    line_chart_pdf,
    line_chart_png,
    paraview_handoff,
    residual_charts,
)

META = SeriesMeta("residual_Ux", "time [s]", "residual [-]", "Ux vs Time (solver log)")


def test_png_pdf_charts_carry_real_bytes():
    png = line_chart_png("residual_Ux", [1.0, 2.0], [0.5, 0.1], META)
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 1000
    pdf = line_chart_pdf("residual_Ux", [1.0, 2.0], [0.5, 0.1], META)
    assert pdf[:5] == b"%PDF-" and len(pdf) > 1000


def test_empty_series_is_missing_not_zero():
    with pytest.raises(ValueError, match="MISSING"):
        line_chart_png("residual_Ux", [], [], META)
    with pytest.raises(ValueError, match="mismatch"):
        line_chart_png("residual_Ux", [1.0], [0.5, 0.1], META)


def test_residual_charts_from_real_log():
    text = ("Time = 1\nSolving for Ux, Initial residual = 0.5\n"
            "Time = 2\nSolving for Ux, Initial residual = 0.1\nEnd\n")
    charts = residual_charts(parse_log(text))
    assert set(charts) == {"Ux"} and charts["Ux"][:8] == b"\x89PNG\r\n\x1a\n"
    pdfs = residual_charts(parse_log(text), fmt="pdf")
    assert pdfs["Ux"][:5] == b"%PDF-"
    with pytest.raises(ValueError, match="MISSING"):
        residual_charts(parse_log(""))


def test_paraview_handoff_real_bytes():
    hand = paraview_handoff("cavity", 1.0, [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)],
                            "p", [0.0, 1.5])
    files = hand["files"]
    assert files["cavity.foam"].startswith(b"# OpenFOAM handoff")
    vtk = files["cavity_t1.vtk"].decode()
    assert "POINTS 2 float" in vtk and "SCALARS p float 1" in vtk
    assert hand["argv"][:1] == ["foamToVTK"]
    with pytest.raises(ValueError, match="MISSING"):
        paraview_handoff("cavity", 1.0, [], "p", [])
    with pytest.raises(ValueError, match="matching"):
        paraview_handoff("cavity", 1.0, [(0.0, 0.0, 0.0)], "p", [0.0, 1.0])
    with pytest.raises(ValueError, match="unsafe"):
        paraview_handoff("a b", 1.0, [(0.0, 0.0, 0.0)], "p", [0.0])
