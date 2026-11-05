"""Log parser + restart plan (W65 SOLV-009, G25/G26)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ResidualSeries:
    field: str
    values: list[float] = field(default_factory=list)
    times: list[float] = field(default_factory=list)


@dataclass
class RunSummary:
    times: list[float] = field(default_factory=list)
    execution_times: list[float] = field(default_factory=list)
    courant: list[float] = field(default_factory=list)
    residuals: dict[str, ResidualSeries] = field(default_factory=dict)
    end_marker: str = "UNKNOWN"  # END | FAILED | UNKNOWN


def parse_log(text: str) -> RunSummary:
    summary = RunSummary()
    for line in text.splitlines():
        match = re.match(r"\s*Time\s*=\s*([0-9.eE+-]+)", line)
        if match:
            try:
                summary.times.append(float(match.group(1)))
            except ValueError:
                pass
        match = re.search(r"ExecutionTime\s*=\s*([0-9.eE+-]+)", line)
        if match:
            try:
                summary.execution_times.append(float(match.group(1)))
            except ValueError:
                pass
        match = re.search(r"Courant\s+(?:Number\s+mean:\s*([0-9.eE+-]+))?", line)
        if match and match.group(1):
            try:
                summary.courant.append(float(match.group(1)))
            except ValueError:
                pass
        match = re.match(r"\s*Solving for (\w+), Initial residual = ([0-9.eE+-]+)", line)
        if match:
            name, value = match.group(1), float(match.group(2))
            series = summary.residuals.setdefault(name, ResidualSeries(name))
            series.values.append(value)
            if summary.times:
                series.times.append(summary.times[-1])
    if "End" in text and re.search(r"\bEnd\b", text):
        summary.end_marker = "END"
    if re.search(r"FOAM (FATAL|aborted|exiting)|Floating point exception", text):
        summary.end_marker = "FAILED"
    return summary


def restart_args(available_times: list[float], requested: str) -> dict:
    """Resolve restart mode without touching the filesystem.

    ``requested`` is ``startTime`` or ``latestTime``. Lexicographic sorting
    is never used; caller supplies numeric times.
    """
    if requested not in ("startTime", "latestTime"):
        raise ValueError("restart must be 'startTime' or 'latestTime'")
    if requested == "latestTime" and not available_times:
        raise ValueError("no time directories available for latestTime restart")
    latest = max(available_times) if available_times else None
    return {"mode": requested, "latest": latest,
            "argv_extra": ["-latestTime"] if requested == "latestTime" else []}
