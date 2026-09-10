"""Framework-neutral cluster partition status model for Wave 79."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClusterServerStatus:
    """One TRUBA lssrv partition row, in documented column order."""

    partition: str
    free_cpus: str = ""
    total_cpus: str = ""
    wait_jobs_resources: str = ""
    wait_jobs_total: str = ""
    nodes_total: str = ""
    max_job_time: str = ""
    min_nodes_per_job: str = ""
    max_nodes_per_job: str = ""
    cores_per_node: str = ""
    memory_mb_per_core: str = ""
    raw_row: str = ""

    @property
    def name(self) -> str:
        """Compatibility alias for callers that treated partitions as names."""
        return self.partition
