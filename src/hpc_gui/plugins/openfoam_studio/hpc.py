"""Slurm/job-draft + SFTP fault model (W65 JOBS-015/SFTP-014, G39-G42).

Draft-only: renders reviewable bash/Slurm text, never submits. The fault
model records per-file stage/commit results for multi-file saves so a
partial failure can never be reported as total success.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


_JOB_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
_PARTITION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
_MODULE_RE = re.compile(r"[A-Za-z0-9_.+-]+(?:/[A-Za-z0-9_.+-]+)*\Z")
_TIME_RE = re.compile(
    r"(?:(?P<days>[0-9]{1,3})-)?(?P<hours>[0-9]{1,3}):"
    r"(?P<minutes>[0-5][0-9]):(?P<seconds>[0-5][0-9])\Z"
)


@dataclass
class SlurmResources:
    nodes: int = 1
    ntasks: int = 1
    time: str = "01:00:00"
    partition: str = ""
    module: str = "apps/openfoam/v2312-2025"


def render_slurm_job(job_name: str, allrun_body: str, res: SlurmResources) -> str:
    if not isinstance(job_name, str) or not _JOB_NAME_RE.fullmatch(job_name):
        raise ValueError("job name must be 1-128 safe ASCII letters, digits, dots, underscores, or hyphens")
    if not isinstance(res, SlurmResources):
        raise TypeError("res must be SlurmResources")
    if type(res.nodes) is not int or type(res.ntasks) is not int or res.nodes < 1 or res.ntasks < 1:
        raise ValueError("Slurm nodes/ntasks must be >= 1")
    if not isinstance(res.time, str):
        raise ValueError("Slurm time must be text in HH:MM:SS or D-HH:MM:SS form")
    match = _TIME_RE.fullmatch(res.time)
    if not match or (match.group("days") and int(match.group("hours")) > 23):
        raise ValueError("Slurm time must be a valid HH:MM:SS or D-HH:MM:SS value")
    if not isinstance(res.partition, str):
        raise ValueError("Slurm partition must be text")
    if res.partition and not _PARTITION_RE.fullmatch(res.partition):
        raise ValueError("Slurm partition contains unsafe characters")
    if not isinstance(res.module, str) or not _MODULE_RE.fullmatch(res.module):
        raise ValueError("module must be a safe slash-separated module name")
    if any(part in (".", "..") for part in res.module.split("/")):
        raise ValueError("module path segments cannot be '.' or '..'")
    if not isinstance(allrun_body, str) or "\x00" in allrun_body:
        raise ValueError("Allrun body must be text without NUL bytes")
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
