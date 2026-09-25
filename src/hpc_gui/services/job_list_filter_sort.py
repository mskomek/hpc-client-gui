"""Framework-neutral Jobs filtering/sorting/selection guards for W28.

Owns HPC-W07-JOB-014..017:

- sort uses semantic values (numeric job ID, elapsed seconds, state rank)
  rather than formatted display strings;
- filter refresh never mutates backend data;
- selection survives refresh only when the identity still exists;
- a stale selection cannot cancel a different row after reorder.
"""

from __future__ import annotations

import re
from typing import Any


_STATE_RANK = {
    "RUNNING": 0,
    "R": 0,
    "PENDING": 1,
    "PD": 1,
    "SUSPENDED": 2,
    "COMPLETED": 3,
    "FAILED": 4,
    "CANCELLED": 5,
    "TIMEOUT": 6,
    "OUT_OF_MEMORY": 7,
    "UNKNOWN": 90,
}


def _row_dict(item: Any) -> dict[str, str]:
    if isinstance(item, dict):
        return {
            "job_id": str(item.get("id", item.get("job_id", ""))).strip(),
            "name": str(item.get("name", "")).strip(),
            "state": str(item.get("state", "")).strip(),
            "partition": str(item.get("partition", "")).strip(),
            "elapsed": str(item.get("elapsed", "")).strip(),
            "nodes": str(item.get("nodes", "")).strip(),
            "cpus": str(item.get("cpus", "")).strip(),
            "reason": str(item.get("reason", item.get("failure_reason", ""))).strip(),
        }
    text = str(item or "").strip()
    if "|" in text:
        parts = [part.strip() for part in text.split("|")]
    else:
        parts = text.split(None, 8)
    return {
        "job_id": parts[0] if parts else text,
        "name": parts[2] if len(parts) > 2 else "",
        "state": parts[4] if len(parts) > 4 else "",
        "partition": parts[1] if len(parts) > 1 else "",
        "elapsed": parts[5] if len(parts) > 5 else "",
        "nodes": parts[6] if len(parts) > 6 else "",
        "cpus": parts[7] if len(parts) > 7 else "",
        "reason": parts[8] if len(parts) > 8 else "",
    }


def matches_filter(item: Any, query: str) -> bool:
    """Case-insensitive match across job_id, name and state."""
    if not str(query or "").strip():
        return True
    needle = str(query).strip().lower()
    row = _row_dict(item)
    return any(needle in row[field].lower() for field in ("job_id", "name", "state"))


def filter_jobs(rows: list[Any], query: str) -> list[Any]:
    """Return a new filtered list; the backend ``rows`` object is untouched."""
    source = list(rows or [])
    if not str(query or "").strip():
        return list(source)
    return [item for item in source if matches_filter(item, query)]


def _elapsed_seconds(value: str) -> float:
    text = str(value or "").strip()
    if not text:
        return -1.0
    # Slurm elapsed forms: [[D-]HH:]MM:SS[.ms] or MM:SS or seconds.
    match = re.match(r"^(?:(\d+)-)?(?:(\d+):)?(\d+):(\d+)(?:\.\d+)?$", text)
    if match:
        days = int(match.group(1) or 0)
        hours = int(match.group(2) or 0)
        minutes = int(match.group(3) or 0)
        seconds = int(match.group(4) or 0)
        return float(days * 86400 + hours * 3600 + minutes * 60 + seconds)
    short = re.match(r"^(\d+):(\d+)(?:\.\d+)?$", text)
    if short:
        return float(int(short.group(1)) * 60 + int(short.group(2)))
    plain = re.match(r"^(\d+(?:\.\d+)?)$", text)
    if plain:
        return float(plain.group(1))
    return float("inf")


def _job_id_key(value: str) -> tuple[int, str, str]:
    """Numeric-aware job-ID sort key (``2`` < ``10`` < ``10_2`` < ``10.batch``)."""
    text = str(value or "").strip()
    match = re.match(r"^(\d+)(.*)$", text)
    if match:
        return (0, int(match.group(1)), match.group(2) or "")
    return (1, text.lower(), "")


def sort_key_for(item: Any, key: str) -> Any:
    """Semantic sort key for one column; never the formatted display string."""
    row = _row_dict(item)
    name = str(key or "").strip().lower()
    if name in {"job_id", "id"}:
        numeric, number, suffix = _job_id_key(row["job_id"])
        return (numeric, number, suffix)
    if name == "elapsed":
        return _elapsed_seconds(row["elapsed"])
    if name == "state":
        rank = _STATE_RANK.get(row["state"].strip().upper(), 50)
        return (rank, row["state"].lower())
    if name in {"nodes", "cpus"}:
        try:
            return (0, float(str(row.get(name, "")).strip() or -1))
        except ValueError:
            return (1, str(row.get(name, "")).lower())
    return str(row.get(name, "")).lower()


def sort_jobs(rows: list[Any], key: str, *, reverse: bool = False) -> list[Any]:
    """Return a new semantically sorted list; the input list is not mutated."""
    source = list(rows or [])
    ordered = sorted(source, key=lambda item: sort_key_for(item, key), reverse=bool(reverse))
    return ordered


def job_ids(rows: list[Any]) -> list[str]:
    """Extract stripped job IDs in order (helper for selection checks)."""
    return [_row_dict(item)["job_id"] for item in (rows or []) if _row_dict(item)["job_id"]]


def selection_still_exists(selected_job_id: str, rows: list[Any]) -> bool:
    """Selection survives a refresh only when the same job ID still exists."""
    wanted = str(selected_job_id or "").strip()
    if not wanted:
        return False
    return wanted in job_ids(rows)


def cancel_target_is_safe(selected_job_id: str, rows: list[Any], requested_job_id: str) -> bool:
    """Stale selections cannot cancel a different row after reorder/filter.

    Cancel is safe only when the requested ID equals the selected ID and the
    selected ID is still present in the current backend rows. This blocks the
    classic reorder race where row N now holds a different job.
    """
    selected = str(selected_job_id or "").strip()
    requested = str(requested_job_id or "").strip()
    if not selected or not requested or selected != requested:
        return False
    return selection_still_exists(selected, rows)
