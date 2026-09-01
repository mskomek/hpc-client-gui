"""Small local analytics model over Job Record Store rows."""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Iterable


def _seconds(value: Any) -> float | None:
    parts = str(value or "").split(":")
    if len(parts) not in (2, 3) or not all(part.isdigit() for part in parts):
        return None
    numbers = [int(part) for part in parts]
    return float(numbers[-1] + 60 * numbers[-2] + (3600 * numbers[-3] if len(numbers) == 3 else 0))


@dataclass(frozen=True)
class DashboardSummary:
    total: int
    states: dict[str, int]
    median_runtime_seconds: float | None
    partitions: dict[str, int]
    cpu_hours: float | None
    gpu_hours: float | None
    array_parents: int
    array_tasks: int
    recent_runs: tuple[dict[str, Any], ...]


class JobHistoryDashboard:
    def summarize(self, records: Iterable[dict[str, Any]], *, profile_id: str | None = None, provider_id: str | None = None, state: str | None = None, since: float | None = None, until: float | None = None, aggregate_arrays: bool = True, limit: int = 100) -> DashboardSummary:
        selected = []
        for record in records:
            if profile_id and record.get("profile_id") != profile_id:
                continue
            if provider_id and record.get("provider_id") != provider_id:
                continue
            if state and str(record.get("state", "")).upper() != state.upper():
                continue
            submitted = float(record.get("submitted_at") or 0)
            if since is not None and submitted < since or until is not None and submitted > until:
                continue
            selected.append(record)
        raw_array_parents = {str(record.get("job_id") or "").split("_", 1)[0] for record in selected if "_" in str(record.get("job_id"))}
        raw_array_tasks = sum("_" in str(record.get("job_id")) for record in selected)
        if aggregate_arrays:
            selected = self._array_parents(selected)
        runtimes = [_seconds(record.get("timing", {}).get("elapsed")) for record in selected]
        runtimes = [value for value in runtimes if value is not None]
        states: dict[str, int] = {}
        partitions: dict[str, int] = {}
        cpu_values = []
        gpu_values = []
        for record in selected:
            job_state = str(record.get("state") or "UNKNOWN").upper()
            states[job_state] = states.get(job_state, 0) + 1
            resources = record.get("resources") if isinstance(record.get("resources"), dict) else {}
            partition = str(resources.get("partition") or "").strip()
            if partition:
                partitions[partition] = partitions.get(partition, 0) + 1
            runtime = _seconds(record.get("timing", {}).get("elapsed"))
            if runtime is not None and str(resources.get("cpus", "")).isdigit():
                cpu_values.append(runtime * int(resources["cpus"]) / 3600)
            if runtime is not None and str(resources.get("gpus", "")).isdigit():
                gpu_values.append(runtime * int(resources["gpus"]) / 3600)
        return DashboardSummary(len(selected), states, statistics.median(runtimes) if runtimes else None, partitions, sum(cpu_values) if cpu_values and len(cpu_values) == len(selected) else None, sum(gpu_values) if gpu_values and len(gpu_values) == len(selected) else None, len(raw_array_parents), raw_array_tasks, tuple(selected[: max(1, min(100, limit))]))

    @staticmethod
    def _array_parents(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        parents: dict[str, dict[str, Any]] = {}
        for record in records:
            parent_id = str(record.get("job_id") or "").split("_", 1)[0]
            if parent_id not in parents or "_" not in str(record.get("job_id")):
                parents[parent_id] = record
        return list(parents.values())
