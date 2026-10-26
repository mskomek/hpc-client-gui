"""Function objects + result browser + plot/export (W65 POST-010, G27-G29)."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass

SUPPORTED_FUNCTION_OBJECTS = ("probes", "forces", "forceCoeffs", "fieldAverage",
                              "yPlus", "wallShearStress", "patchAverage")


def render_function_object(name: str, params: dict) -> str:
    if name not in SUPPORTED_FUNCTION_OBJECTS:
        raise ValueError(f"function object '{name}' is RAW-ADVANCED only (no typed schema)")
    body = "\n".join(f"    {k} {v};" for k, v in params.items())
    return (f"{name}\n{{\n    type {name};\n    libs (\"libfieldFunctionObjects.so\");\n"
            f"{body}\n}}\n")


@dataclass(frozen=True)
class TimeDir:
    name: str
    value: float | None


def list_time_dirs(names: list[str]) -> list[TimeDir]:
    out = []
    for name in names:
        try:
            out.append(TimeDir(name, float(name)))
        except ValueError:
            if re.fullmatch(r"\d+(\.\d+)?", name):
                out.append(TimeDir(name, float(name)))
            else:
                out.append(TimeDir(name, None))
    return out


def result_status(time_dirs: list[str], postprocessing: list[str]) -> dict:
    numeric = [t for t in list_time_dirs(time_dirs) if t.value is not None]
    if not numeric and not postprocessing:
        return {"status": "MISSING", "detail": "no time directories or postProcessing artifacts"}
    return {"status": "PRESENT", "times": len(numeric),
            "post": len(postprocessing), "latest": max((t.value for t in numeric), default=None)}


def residuals_csv(field: str, times: list[float], values: list[float]) -> str:
    if len(times) != len(values):
        raise ValueError("times/values length mismatch; refusing to fabricate chart data")
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["time", f"residual_{field}"])
    for t, v in zip(times, values):
        writer.writerow([t, v])
    return buf.getvalue()


def metric_report(kind: str, value: float, units: str, formula: str,
                  inputs_present: bool) -> dict:
    if not inputs_present:
        return {"kind": kind, "status": "MISSING",
                "detail": "required sampled quantities absent; value not computed"}
    return {"kind": kind, "value": value, "units": units,
            "formula": formula, "provenance": "computed-from-case-data"}
