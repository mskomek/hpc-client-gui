"""Framework-neutral normalization helpers for scheduler job rows."""

from __future__ import annotations


def parse_job_row(item: dict[str, object] | str) -> dict[str, str]:
    """Extract a normalized row from a scheduler mapping or a formatted row."""
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
    text = str(item).strip()
    parts = [part.strip() for part in text.split("|")] if "|" in text else text.split(None, 8)
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


def prepare_job_list(
    items: list[object],
    *,
    query: str = "",
    hide_finished: bool = False,
    sort_key: str = "",
    reverse: bool = False,
) -> list[object]:
    """Filter and sort backend job records without changing the input list."""
    from hpc_gui.services.job_list_filter_sort import filter_jobs, sort_jobs
    from hpc_gui.services.jobs_history import job_sort_key
    from hpc_gui.services.slurm_models import is_terminal_state

    filtered = filter_jobs(list(items or []), query)
    if hide_finished:
        filtered = [item for item in filtered if not is_terminal_state(parse_job_row(item)["state"])]
    if sort_key:
        return sort_jobs(filtered, sort_key, reverse=bool(reverse))
    return sorted(filtered, key=job_sort_key)
