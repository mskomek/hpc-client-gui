"""Slurm/job-draft + SFTP fault model (W65 JOBS-015/SFTP-014, G39-G42).

Draft-only: renders reviewable bash/Slurm text, never submits. The fault
model records per-file stage/commit results for multi-file saves so a
partial failure can never be reported as total success.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SlurmResources:
    nodes: int = 1
    ntasks: int = 1
    time: str = "01:00:00"
    partition: str = ""
    module: str = "apps/openfoam/v2312-2025"


def render_slurm_job(job_name: str, allrun_body: str, res: SlurmResources) -> str:
    if not job_name or any(c in job_name for c in " \t\n;|&$`"):
        raise ValueError("unsafe job name")
    if res.nodes < 1 or res.ntasks < 1:
        raise ValueError("Slurm nodes/ntasks must be >= 1")
    header = ["#!/bin/bash", f"#SBATCH --job-name={job_name}",
              f"#SBATCH --nodes={res.nodes}", f"#SBATCH --ntasks={res.ntasks}",
              f"#SBATCH --time={res.time}"]
    if res.partition:
        header.append(f"#SBATCH --partition={res.partition}")
    return "\n".join(header + [f"module load {res.module}",
                              "# DRAFT ONLY - review before sbatch; never auto-submitted",
                              allrun_body]) + "\n"


@dataclass
class FileStage:
    relpath: str
    sha_before: str
    sha_staged: str
    committed: bool = False
    error: str = ""


@dataclass
class MultiFileCommit:
    files: list[FileStage] = field(default_factory=list)

    def overall(self) -> str:
        if not self.files:
            return "EMPTY"
        if all(f.committed for f in self.files):
            return "COMMITTED"
        if any(f.committed for f in self.files):
            failed = [f.relpath for f in self.files if not f.committed]
            return f"PARTIAL: committed {sum(f.committed for f in self.files)}/{len(self.files)}; failed: {failed}"
        return "FAILED"


def plan_ranks_match(n_subdomains: int, ntasks: int) -> None:
    if n_subdomains != ntasks:
        raise ValueError(f"rank mismatch: decompose {n_subdomains} != Slurm ntasks {ntasks}")
