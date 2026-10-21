"""Queue, accounting, and archived-history callbacks for the Jobs shell."""

from __future__ import annotations

import time


def make_history_callbacks(context):
    def list_jobs():
        from hpc_gui.services.jobs_history import job_sort_key, merge_job_sources, parse_sacct_history

        slurm = context.resolve_slurm()
        profile = context.resolve_profile()
        scope = context.profile_identity()
        store = context.job_store()
        if not slurm:
            jobs = []
            for record in store.list(
                profile_id=scope["profile_id"],
                cluster_id=scope["cluster_id"],
                provider_id=scope["provider_id"],
            ):
                row = {
                    **record.get("metadata", {}),
                    **record.get("paths", {}),
                    **record.get("resources", {}),
                    "job_id": record["job_id"],
                    "id": record["job_id"],
                    "state": record.get("state", ""),
                    "source": "local_archive",
                }
                jobs.append(row)
            return {
                "jobs": sorted(jobs, key=job_sort_key),
                "active_job_ids": (),
                "history_stale": True,
                "history_error": "No active scheduler connection; showing saved jobs.",
            }

        username = str(profile.get("username", ""))
        owner_state = context.state
        history_days = int(owner_state.get("_jobs_history_days", 7))
        if history_days not in {7, 30, 90, 365}:
            history_days = 7
        squeue_result = getattr(slurm, "squeue_result", None)
        response = squeue_result(username) if callable(squeue_result) else slurm.squeue(username)
        if getattr(response, "ok", True) is False:
            raise RuntimeError(getattr(response, "message", "squeue is unavailable"))
        raw = getattr(response, "stdout", response)
        rows = _parse_queue_rows(raw)
        cache = owner_state.setdefault("_jobs_history_cache", {})
        identity = (
            str(profile.get("id", profile.get("profile_id", ""))),
            str(profile.get("cluster_id", "")),
            str(profile.get("provider_id", "")),
            username,
            history_days,
        )
        entry = cache.setdefault(
            identity, {"rows": [], "read_at": -60.0, "error": "", "active_ids": None}
        )
        active_ids = frozenset(row["job_id"] for row in rows)
        queue_changed = entry["active_ids"] is not None and active_ids != entry["active_ids"]
        first_queue_read = entry["active_ids"] is None
        entry["active_ids"] = active_ids
        stale = False
        if first_queue_read or queue_changed or time.monotonic() - entry["read_at"] >= 60:
            try:
                accounting = _query_accounting(slurm, username, history_days)
                entry["rows"] = parse_sacct_history(str(accounting or ""))
                entry["read_at"] = time.monotonic()
                entry["error"] = ""
            except Exception as error:
                entry["error"] = str(error) or "sacct is unavailable"
                stale = True
        else:
            stale = bool(entry["error"])

        merged = merge_job_sources(rows, entry["rows"])
        archived = store.list(
            profile_id=scope["profile_id"],
            cluster_id=scope["cluster_id"],
            provider_id=scope["provider_id"],
        )
        _merge_archived_rows(merged, archived)
        _persist_observations(store, scope, merged)
        merged.sort(key=job_sort_key)
        return {
            "jobs": merged,
            "active_job_ids": tuple(row["job_id"] for row in rows),
            "history_stale": stale,
            "history_error": entry["error"],
        }

    def set_history_days(days):
        value = int(days)
        if value not in {7, 30, 90, 365}:
            raise ValueError("unsupported history window")
        if isinstance(context.session_state, dict):
            context.session_state["_jobs_history_days"] = value
        return value

    def can_load_older_history():
        slurm = context.resolve_slurm()
        return callable(getattr(slurm, "sacct_history_result", None))

    return {
        "list_jobs": list_jobs,
        "set_history_days": set_history_days,
        "can_load_older_history": can_load_older_history,
    }


def _parse_queue_rows(raw):
    rows = []
    for line in str(raw or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.lower().startswith("jobid"):
            continue
        parts = [part.strip() for part in stripped.split("|")]
        if len(parts) < 6:
            continue
        fields = (
            "job_id", "partition", "name", "user", "state", "elapsed",
            "nodes", "cpus", "reason", "submit_time",
        )
        row = {field: parts[index] if index < len(parts) else "" for index, field in enumerate(fields)}
        row.update({"id": row["job_id"], "source": "squeue"})
        rows.append(row)
    if rows or not str(raw or "").strip():
        return rows
    from hpc_gui.services.slurm_models import parse_squeue_result

    return [
        {
            "id": job.job_id,
            "job_id": job.job_id,
            "name": job.name,
            "state": job.state,
            "partition": job.partition,
            "elapsed": job.elapsed,
            "nodes": job.nodes,
            "cpus": job.cpus,
            "reason": job.reason,
            "user": job.user,
            "source": "squeue",
        }
        for job in parse_squeue_result(raw)
    ]


def _query_accounting(slurm, username, history_days):
    for name, arguments in (
        ("sacct_history_result", (username, history_days)),
        ("sacct_result", (username,)),
    ):
        query = getattr(slurm, name, None)
        if callable(query):
            response = query(*arguments)
            if getattr(response, "ok", True) is False:
                raise RuntimeError(getattr(response, "message", "sacct is unavailable"))
            return getattr(response, "stdout", response)
    return slurm.sacct(username)


def _merge_archived_rows(merged, archived):
    by_id = {str(row.get("job_id", "")): row for row in merged}
    for record in archived:
        job_id = str(record.get("job_id", ""))
        metadata = dict(record.get("metadata") or {})
        metadata.update(record.get("paths") or {})
        restored = {
            **metadata,
            **(record.get("resources") or {}),
            "job_id": job_id,
            "id": job_id,
            "state": record.get("state", ""),
            "source": "local_archive",
        }
        row = by_id.get(job_id)
        if row is None:
            merged.append(restored)
            by_id[job_id] = restored
            continue
        for key, value in restored.items():
            if row.get(key) in (None, "", "-") and value not in (None, "", "-"):
                row[key] = value


def _persist_observations(store, scope, rows):
    metadata_fields = (
        "name", "user", "partition", "reason", "exit_code", "failure_reason",
        "array_job_id", "array_task_id", "dependency", "heterogeneous_id",
        "script_text", "script_hash", "raw_details", "raw_accounting",
    )
    resource_fields = ("nodes", "cpus", "nodelist", "resources", "elapsed")
    timing_fields = ("submit_time", "start_time", "end_time", "updated_at")
    path_fields = (
        "submit_directory", "workdir", "workdir_source", "script_path",
        "stdout_path", "stderr_path",
    )
    for row in rows:
        store.record_observation({
            **scope,
            "job_id": row.get("job_id", row.get("id", "")),
            "state": row.get("state", ""),
            "source": row.get("source", "observed"),
            "metadata": _known_fields(row, metadata_fields),
            "resources": _known_fields(row, resource_fields),
            "timing": _known_fields(row, timing_fields),
            "paths": _known_fields(row, path_fields),
        })


def _known_fields(row, fields):
    return {key: row[key] for key in fields if row.get(key) not in (None, "", "-")}
