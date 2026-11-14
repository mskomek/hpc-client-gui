"""W65 POST-010: chart/status and residual parsing against a real ESI v2312 result."""

from __future__ import annotations

from pathlib import Path

import pytest

from hpc_gui.plugins.openfoam_studio.post import (
    list_time_dirs,
    metric_report,
    parse_residual_series,
    parse_probe_series,
    residuals_csv,
    result_status,
)
from hpc_gui.plugins.openfoam_studio.plot_export import paraview_handoff

FIXTURES = Path(__file__).parent / "fixtures" / "post010"
LISTING = FIXTURES / "cavity_listing.txt"
LOG = FIXTURES / "log.icoFoam"
PROBES_P = FIXTURES / "probes_p.txt"
PROBES_U = FIXTURES / "probes_U.txt"


def listing_names() -> list[str]:
    return [line.strip() for line in LISTING.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_listing_fixture_is_the_recorded_cavity_case():
    assert listing_names() == [
        "0", "0.1", "0.2", "0.3", "0.4", "0.5", "constant", "log.blockMesh", "log.icoFoam", "system",
    ]


def test_real_v2312_time_dirs_are_numeric():
    dirs = list_time_dirs(listing_names())
    numeric = [d for d in dirs if d.value is not None]
    assert [d.value for d in numeric] == [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
    assert [d.name for d in dirs if d.value is None] == ["constant", "log.blockMesh", "log.icoFoam", "system"]


def test_real_v2312_result_status_reports_present_with_latest_time():
    status = result_status(listing_names(), [])
    assert status == {"status": "PRESENT", "times": 6, "post": 0, "latest": 0.5}


def test_empty_case_is_missing_not_fabricated():
    assert result_status([], [])["status"] == "MISSING"
    assert result_status(["constant", "system"], [])["status"] == "MISSING"


def test_postprocessing_only_case_is_present():
    status = result_status([], ["postProcessing/forces/0/forces.dat"])
    assert status["status"] == "PRESENT"
    assert status["times"] == 0
    assert status["post"] == 1


def test_residual_parser_reads_the_real_icoFoam_log():
    series = parse_residual_series(LOG.read_text(encoding="utf-8"))
    assert set(series) == {"Ux", "Uy", "p"}
    ux = series["Ux"]
    assert len(ux) == 100
    assert ux[0] == (0.005, 1.0)
    assert ux[-1] == (0.5, 2.3091e-07)
    assert all(time <= 0.5 for time, _ in ux)


def test_pressure_loop_keeps_every_point():
    series = parse_residual_series(LOG.read_text(encoding="utf-8"))
    pressures = series["p"]
    assert len(pressures) == 200
    assert pressures[0][0] == 0.005
    assert pressures[-1][0] == 0.5


def test_residual_csv_over_the_parsed_series():
    series = parse_residual_series(LOG.read_text(encoding="utf-8"))
    times = [t for t, _ in series["Ux"]]
    values = [v for _, v in series["Ux"]]
    csv_text = residuals_csv("Ux", times, values)
    rows_out = csv_text.strip().splitlines()
    assert rows_out[0] == "time,residual_Ux"
    assert len(rows_out) == 101
    assert rows_out[-1] == "0.5,2.3091e-07"


def test_parser_without_time_header_yields_nothing():
    assert parse_residual_series("Solving for Ux, Initial residual = 1\n") == {}
    assert parse_residual_series("") == {}


def test_metric_without_inputs_is_missing():
    report = metric_report("delta_p", 1.0, "Pa", "p_out - p_in", inputs_present=False)
    assert report["status"] == "MISSING"
    assert "value" not in report


def test_probe_scalar_series_from_the_real_probes_file():
    times, values = parse_probe_series(PROBES_P.read_text(encoding="utf-8"))
    assert len(times) == 100
    assert times[0] == 0.005
    assert times[-1] == 0.5
    assert values[0] == 0.645768
    assert values[-1] == -0.00133453


def test_probe_vector_components_come_from_the_same_rows():
    times_x, values_x = parse_probe_series(PROBES_U.read_text(encoding="utf-8"), component=0)
    times_z, values_z = parse_probe_series(PROBES_U.read_text(encoding="utf-8"), component=2)
    assert times_x == times_z
    assert len(values_x) == 100
    assert values_x[0] == -0.0541835
    assert set(values_z) == {0.0}


def test_probe_component_out_of_range_yields_nothing():
    assert parse_probe_series(PROBES_P.read_text(encoding="utf-8"), component=3) == ([], [])


def test_chart_png_renders_from_the_real_probe_series():
    pytest.importorskip("matplotlib")
    from hpc_gui.plugins.openfoam_studio.plot_export import SeriesMeta, line_chart_png

    times, values = parse_probe_series(PROBES_P.read_text(encoding="utf-8"))
    png = line_chart_png(
        "probe p",
        times,
        values,
        SeriesMeta(label="probe p", x_units="s", y_units="m2/s2", formula="p at (0.05 0.05 0.005)"),
    )
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(png) > 1000


def test_chart_refuses_an_empty_series():
    pytest.importorskip("matplotlib")
    from hpc_gui.plugins.openfoam_studio.plot_export import SeriesMeta, line_chart_png

    with pytest.raises(ValueError):
        line_chart_png("empty", [], [], SeriesMeta(label="empty", x_units="s", y_units="-", formula="-"))


def test_chart_pdf_renders_from_the_real_probe_series():
    pytest.importorskip("matplotlib")
    from hpc_gui.plugins.openfoam_studio.plot_export import SeriesMeta, line_chart_pdf

    times, values = parse_probe_series(PROBES_P.read_text(encoding="utf-8"))
    pdf = line_chart_pdf(
        "probe p",
        times,
        values,
        SeriesMeta(label="probe p", x_units="s", y_units="m2/s2", formula="p at (0.05 0.05 0.005)"),
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_paraview_handoff_carries_a_real_probe_sample():
    times, values = parse_probe_series(PROBES_P.read_text(encoding="utf-8"))
    handoff = paraview_handoff(
        "cavity",
        times[-1],
        [(0.05, 0.05, 0.005)],
        "p",
        [values[-1]],
    )
    files = handoff["files"]
    assert set(files) == {"cavity.foam", "cavity_t0.5.vtk"}
    assert files["cavity.foam"].startswith(b"# OpenFOAM handoff stub")
    vtk = files["cavity_t0.5.vtk"].decode("ascii")
    assert "POINTS 1 float" in vtk
    assert "POINT_DATA 1" in vtk
    assert "SCALARS p float 1" in vtk
    assert handoff["argv"][:1] == ["foamToVTK"]


def test_paraview_handoff_refuses_missing_or_unsafe_input():
    with pytest.raises(ValueError):
        paraview_handoff("cavity", 0.5, [], "p", [])
    with pytest.raises(ValueError):
        paraview_handoff("cavity", 0.5, [(0.0, 0.0, 0.0)], "p", [1.0, 2.0])
    with pytest.raises(ValueError):
        paraview_handoff("bad/name", 0.5, [(0.0, 0.0, 0.0)], "p", [1.0])
