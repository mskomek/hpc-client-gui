"""Merge live queue rows with recent Slurm accounting history."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Iterable

from .slurm_models import is_terminal_state


_JOB_ID = re.compile(r"^\d+(?:_\d+|\[[^]]+\])?$")
_STEP_ID = re.compile(r"^\d+(?:_\d+)?\.(?:batch|extern|\d+)$", re.I)


def _job_id(row: dict[str, Any]) -> str:
    return str(row.get("job_id", row.get("id", ""))).strip()


def _time_key(value: Any) -> float:
    text = str(value or "").strip()
    if not text or text in {"Unknown", "N/A", "None", "-"}:
        return -1.0
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:19], fmt).timestamp()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return -1.0


def _id_key(value: str) -> tuple[int, str]:
    match = re.match(r"^(\d+)(.*)$", value)
    return (int(match.group(1)), match.group(2)) if match else (-1, value)


def parse_sacct_history(text: str) -> list[dict[str, str]]:
    """Parse the configured pipe format; ignore array steps and step records."""
    rows = []
    for line in str(text or "").splitlines():
        parts = [part.strip() for part in line.strip().split("|")]
        if len(parts) < 4 or parts[0].lower() in {"jobid", "jobidraw"}:
            continue
        if not _JOB_ID.fullmatch(parts[0]) or _STEP_ID.fullmatch(parts[0]):
            continue
        if len(parts) <= 7:
            # Compatibility with pre-v2 provider templates.
            parts += [""] * (7 - len(parts))
            rows.append({
                "id": parts[0], "job_id": parts[0], "name": parts[1],
                "partition": "", "state": parts[2].split()[0],
                "elapsed": parts[3], "max_rss": parts[4],
                "alloc_tres": parts[5], "exit_code": parts[6],
                "source": "sacct",
            })
            continue
        parts += [""] * (14 - len(parts))
        rows.append({
            "id": parts[0], "job_id": parts[0], "name": parts[1],
            "partition": parts[2], "state": parts[3].split()[0],
            "elapsed": parts[4], "nodes": parts[5], "cpus": parts[6],
            "reason": parts[7], "exit_code": parts[8],
            "submit_time": parts[9], "end_time": parts[10],
            "workdir": parts[11], "stdout_path": parts[12],
            "stderr_path": parts[13], "source": "sacct",
        })
    return rows


def merge_job_sources(
    active_rows: Iterable[dict[str, Any]],
    history_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Deduplicate queue/accounting rows and keep array tasks, never steps."""
    merged: dict[str, dict[str, Any]] = {}
    active_ids: set[str] = set()
    for source, is_active in ((history_rows, False), (active_rows, True)):
        for item in source or ():
            row = dict(item)
            job_id = _job_id(row)
            if not job_id or not _JOB_ID.fullmatch(job_id) or _STEP_ID.fullmatch(job_id):
                continue
            current = merged.setdefault(job_id, {})
            current.update({key: value for key, value in row.items() if value not in (None, "", "-")})
            current["id"] = current["job_id"] = job_id
            if is_active:
                active_ids.add(job_id)
                current["source"] = "squeue"
    # sacct may emit an array parent summary alongside its individual tasks.
    # Prefer the task records so each selectable row has one Slurm identity.
    task_parents = {job_id.split("_", 1)[0] for job_id in merged if "_" in job_id}
    for parent in task_parents:
        if parent not in active_ids:
            merged.pop(parent, None)
    return sorted(merged.values(), key=job_sort_key)


def job_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    """Active first; recent submissions/runs first within each section."""
    state = str(row.get("state", "")).strip().upper()
    job_id = _job_id(row)
    if not is_terminal_state(state):
        stamp = _time_key(row.get("submit_time"))
        if stamp < 0:
            # Keep provider/squeue ordering when the provider omits submit time.
            return (0, 0, 0)
        return (0, -stamp, tuple(-part if isinstance(part, int) else part for part in _id_key(job_id)))
    end = _time_key(row.get("end_time"))
    return (1, -end, tuple(-part if isinstance(part, int) else part for part in _id_key(job_id)))

