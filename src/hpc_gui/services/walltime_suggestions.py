"""Explainable walltime advice from successful local job records."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable


def _seconds(value: Any) -> int | None:
    parts = str(value or "").split(":")
    if len(parts) not in (2, 3) or not all(part.isdigit() for part in parts):
        return None
    values = [int(part) for part in parts]
    return values[-1] + 60 * values[-2] + (3600 * values[-3] if len(values) == 3 else 0)


@dataclass(frozen=True)
class WalltimeSuggestion:
    seconds: int
    p90_seconds: int
    sample_count: int
    margin_seconds: int
    reason: str

    def as_slurm_time(self) -> str:
        hours, remainder = divmod(self.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def suggest_walltime(records: Iterable[dict[str, Any]], target: dict[str, Any], *, minimum_samples: int = 5) -> WalltimeSuggestion | None:
    wanted = {key: target.get(key) for key in ("provider_id", "template_id", "partition", "nodes", "cpus", "gpus")}
    durations = []
    for record in records:
        if str(record.get("state") or "").upper() != "COMPLETED":
            continue
        resources = record.get("resources") if isinstance(record.get("resources"), dict) else {}
        actual = {key: record.get(key) if key in {"provider_id", "template_id"} else resources.get(key) for key in wanted}
        if any(wanted[key] is not None and actual[key] != wanted[key] for key in wanted):
            continue
        duration = _seconds((record.get("timing") or {}).get("elapsed"))
        if duration is not None and duration > 0:
            durations.append(duration)
    if len(durations) < max(1, minimum_samples):
        return None
    durations.sort()
    p90 = durations[math.floor((len(durations) - 1) * 0.9)]
    margin = max(60, math.ceil(p90 * 0.1))
    recommended = math.ceil((p90 + margin) / 300) * 300
    return WalltimeSuggestion(recommended, p90, len(durations), margin, "P90 of successful similar jobs plus a 10% safety margin, rounded up to 5 minutes.")
