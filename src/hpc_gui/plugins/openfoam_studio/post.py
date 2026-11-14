"""Function objects + result browser + plot/export (W65 POST-010, G27-G29)."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass

SUPPORTED_FUNCTION_OBJECTS = ("probes", "forces", "forceCoeffs", "fieldAverage",
                              "yPlus", "wallShearStress", "patchAverage")

_LOG_TIME = re.compile(r"^Time = ([0-9.eE+-]+)\s*$")
_LOG_RESIDUAL = re.compile(r"Solving for ([A-Za-z0-9_]+), Initial residual = ([0-9.eE+-]+)")


def parse_residual_series(log_text: str) -> dict[str, list[tuple[float, float]]]:
    """Return {field: [(time, initial residual), ...]} from a solver log.

    Only lines the solver actually wrote are used: a "Time =" header sets the
    current time and each "Solving for <field>, Initial residual = <value>"
    appends a point. Pressure loops can record several points per time, and that
    is kept rather than averaged away (W65 POST-010).
    """
    series: dict[str, list[tuple[float, float]]] = {}
    current = None
    for line in log_text.splitlines():
        match = _LOG_TIME.match(line.strip())
        if match:
            current = float(match.group(1))
            continue
        match = _LOG_RESIDUAL.search(line)
        if match and current is not None:
            series.setdefault(match.group(1), []).append((current, float(match.group(2))))
    return series


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


def parse_probe_series(text: str, *, component: int = 0) -> tuple[list[float], list[float]]:
    """Return (times, values) from a probes file for one component.

    Lines starting with # are the probes header; every other line is a time
    followed by a scalar or a vector. Nothing is interpolated: a malformed line
    is skipped rather than turned into a point (W65 POST-010).
    """
    times: list[float] = []
    values: list[float] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.replace("(", " ").replace(")", " ").split()
        if len(parts) < 2:
            continue
        try:
            time_value = float(parts[0])
            numbers = [float(p) for p in parts[1:]]
        except ValueError:
            continue
        if not 0 <= component < len(numbers):
            continue
        times.append(time_value)
        values.append(numbers[component])
    return times, values
