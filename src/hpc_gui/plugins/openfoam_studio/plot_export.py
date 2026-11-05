"""Chart/report export + viewer handoff over real result bytes (W65 POST-010, G29).

PNG/PDF charts are rendered from caller-supplied sampled series only;
empty inputs yield MISSING, never fabricated zeros. The ParaView/VTK
handoff writes a real ``.foam`` stub plus a ``foamToVTK`` argv preview and,
when result bytes are supplied, a minimal ASCII VTK artifact carrying the
stated series. Backend: matplotlib Agg (headless-safe).
"""

from __future__ import annotations

import io
from dataclasses import dataclass


@dataclass(frozen=True)
class SeriesMeta:
    label: str
    x_units: str
    y_units: str
    formula: str
    provenance: str = "computed-from-case-data"


def _require_real(label: str, xs: list[float], ys: list[float]) -> None:
    if not xs or not ys:
        raise ValueError(f"chart '{label}': no sampled result bytes (MISSING, not zero)")
    if len(xs) != len(ys):
        raise ValueError(f"chart '{label}': x/y length mismatch; refusing to fabricate points")


def _mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def line_chart_png(label: str, xs: list[float], ys: list[float],
                   meta: SeriesMeta) -> bytes:
    _require_real(label, xs, ys)
    plt = _mpl()
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    try:
        ax.plot(xs, ys, marker="o", markersize=3)
        ax.set_title(f"{label}  [{meta.y_units} vs {meta.x_units}]")
        ax.set_xlabel(meta.x_units)
        ax.set_ylabel(meta.y_units)
        fig.text(0.01, 0.01, meta.formula, fontsize=6)
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        return buf.getvalue()
    finally:
        plt.close(fig)


def line_chart_pdf(label: str, xs: list[float], ys: list[float],
                   meta: SeriesMeta) -> bytes:
    _require_real(label, xs, ys)
    plt = _mpl()
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    try:
        ax.plot(xs, ys, marker="o", markersize=3)
        ax.set_title(f"{label}  [{meta.y_units} vs {meta.x_units}]")
        ax.set_xlabel(meta.x_units)
        ax.set_ylabel(meta.y_units)
        fig.text(0.01, 0.01, f"{meta.formula} | {meta.provenance}", fontsize=6)
        buf = io.BytesIO()
        fig.savefig(buf, format="pdf")
        return buf.getvalue()
    finally:
        plt.close(fig)


def residual_charts(summary, fmt: str = "png") -> dict[str, bytes]:
    """Render one chart per residual series from a real RunSummary."""
    out: dict[str, bytes] = {}
    for name, series in summary.residuals.items():
        meta = SeriesMeta(f"residual_{name}", "time [s]", "residual [-]",
                          f"Initial residual {name} vs Time (solver log)")
        if fmt == "pdf":
            out[name] = line_chart_pdf(f"residual_{name}", series.times,
                                       series.values, meta)
        else:
            out[name] = line_chart_png(f"residual_{name}", series.times,
                                       series.values, meta)
    if not out:
        raise ValueError("no residual series sampled (MISSING, not zero)")
    return out


def paraview_handoff(case_name: str, time_value: float,
                     points: list[tuple[float, float, float]],
                     field: str, values: list[float]) -> dict[str, bytes | list[str]]:
    """Viewer handoff: real .foam stub + ASCII VTK carrying supplied samples.

    ``points``/``values`` must be non-empty real samples; a tractable small
    dataset is expected (guarded at 100k points).
    """
    if not points or not values or len(points) != len(values):
        raise ValueError("viewer handoff needs matching non-empty points/values (MISSING)")
    if len(points) > 100000:
        raise ValueError("viewer handoff capped at 100k sample points")
    if not case_name or any(c in case_name for c in " \t\n;|&$`\"'\\/"):
        raise ValueError(f"unsafe case name '{case_name}'")
    foam = f"# OpenFOAM handoff stub for {case_name} t={time_value:g}\n".encode()
    lines = ["# vtk DataFile Version 2.0", f"OpenFOAM {case_name} t={time_value:g}",
             "ASCII", "DATASET POLYDATA",
             f"POINTS {len(points)} float"]
    lines += [f"{x:g} {y:g} {z:g}" for x, y, z in points]
    lines += [f"POINT_DATA {len(values)}", f"SCALARS {field} float 1",
              "LOOKUP_TABLE default"] + [f"{v:g}" for v in values]
    vtk = ("\n".join(lines) + "\n").encode()
    return {"files": {f"{case_name}.foam": foam, f"{case_name}_t{time_value:g}.vtk": vtk},
            "argv": ["foamToVTK", "-case", ".", "-time", f"{time_value:g}"],
            "provenance": "viewer-handoff:w65r2 (external ParaView required)"}
