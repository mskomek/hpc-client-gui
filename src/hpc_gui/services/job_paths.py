"""Resolve a selected job's best known remote directory with provenance."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping


@dataclass(frozen=True)
class ResolvedJobDirectory:
    path: str
    source: str
    verified: bool


def resolve_job_directory(job: Mapping[str, Any] | Any) -> ResolvedJobDirectory:
    """Apply the documented WorkDir/accounting/provenance/output fallback order."""
    data = job if isinstance(job, Mapping) else vars(job)
    workdir = str(data.get("workdir") or "").strip()
    if workdir:
        source = str(data.get("workdir_source") or data.get("source") or "slurm_workdir")
        if source == "local_archive":
            return ResolvedJobDirectory(workdir, "local_snapshot", False)
        return ResolvedJobDirectory(workdir, source, True)
    candidates = (
        ("accounting_workdir", "sacct_workdir", True),
        ("last_workdir", "local_snapshot", False),
        ("submit_directory", "submit_directory", False),
        ("submit_workdir", "submit_chdir", False),
    )
    for key, source, verified in candidates:
        path = str(data.get(key) or "").strip()
        if path:
            return ResolvedJobDirectory(path, source, verified)
    for key, source in (("stdout_path", "output_parent"),
                        ("stderr_path", "output_parent"),
                        ("script_path", "script_parent")):
        path = str(data.get(key) or "").strip()
        parent = str(PurePosixPath(path).parent) if path else ""
        if parent not in {"", "."}:
            return ResolvedJobDirectory(parent, source, False)
    return ResolvedJobDirectory("", "unavailable", False)
