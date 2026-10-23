"""Validated user parameters for a Journal Studio -> Slurm job draft.

Every value that lands in an ``#SBATCH`` directive or the script body passes
an allowlist here first. Paths are absolute POSIX paths without traversal
segments; the journal path is relative to the working directory.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import PurePosixPath


class SlurmDraftError(ValueError):
    """Raised with every blocking input problem at once."""

    def __init__(self, errors: list[str] | tuple[str, ...]):
        self.errors: tuple[str, ...] = tuple(errors)
        super().__init__("; ".join(self.errors) or "invalid Slurm draft request")


@dataclass(frozen=True, slots=True)
class SlurmDraftRequest:
    """Raw user input as typed in the UI; numbers stay strings until validated."""

    workdir: str
    journal_path: str
    partition: str
    account: str
    job_name: str = "journal_studio"
    nodes: str = "1"
    cpus_per_task: str = "56"
    walltime: str = "00:30:00"
    fluent_version: str = "25.2"
    dimension: str = "3d"
    precision: str = "dp"


@dataclass(frozen=True, slots=True)
class ResolvedDraft:
    """Normalized, allowlisted values ready for the script template."""

    job_name: str
    partition: str
    account: str
    cpus_per_task: int
    walltime: str
    workdir: str
    journal_path: str
    journal_remote_path: str
    fluent_bin_dir: str
    fluent_mode: str
    script_name: str
    script_path: str


_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
_JOB_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,62}")
_PATH_RE = re.compile(r"[A-Za-z0-9_@+./-]+")
_WALLTIME_RE = re.compile(r"(?:\d{1,3}-)?\d{1,3}:[0-5]\d:[0-5]\d")
_VERSION_RE = re.compile(r"\d{2}\.\d")
_MAX_PATH_LENGTH = 1024
_MAX_CPUS = 128  # shortcut: sanity bound for one node, not a cluster limit; upgrade to provider config


def _check_workdir(value: str) -> str | None:
    if not value.startswith("/") or not _PATH_RE.fullmatch(value) or len(value) > _MAX_PATH_LENGTH:
        return "working directory must be an absolute POSIX path (letters, digits and _@+./- only)"
    if any(part in ("", ".", "..") for part in value.split("/")[1:]):
        return "working directory must not contain '.', '..' or empty segments"
    return None


def _check_journal(value: str) -> str | None:
    if value.startswith(("/", "-")) or not _PATH_RE.fullmatch(value) or len(value) > _MAX_PATH_LENGTH:
        return "journal path must be relative to the working directory (letters, digits and _@+./- only)"
    if any(part in ("", ".", "..") for part in value.split("/")):
        return "journal path must not contain '.', '..' or empty segments"
    return None


def _cpus(text: str, errors: list[str]) -> int:
    try:
        value = int(text.strip())
    except ValueError:
        errors.append("cpus per task must be an integer")
        return 0
    if not 1 <= value <= _MAX_CPUS:
        errors.append(f"cpus per task must be between 1 and {_MAX_CPUS}")
    return value


def _walltime(text: str, errors: list[str]) -> str:
    value = text.strip()
    if not _WALLTIME_RE.fullmatch(value) or not re.search(r"[1-9]", value):
        errors.append("walltime must be non-zero and in [D-]HH:MM:SS form")
    return value


def resolve_request(request: SlurmDraftRequest) -> ResolvedDraft:
    """Validate every field and return normalized values, or raise SlurmDraftError."""
    errors: list[str] = []
    workdir = request.workdir.strip()
    journal = request.journal_path.strip()
    job_name = request.job_name.strip()
    partition = request.partition.strip()
    account = request.account.strip()

    for message in (_check_workdir(workdir), _check_journal(journal)):
        if message:
            errors.append(message)
    if not job_name or not _JOB_NAME_RE.fullmatch(job_name):
        errors.append("job name must start with a letter and use letters, digits, _, . or -")
    if not _NAME_RE.fullmatch(partition):
        errors.append("partition is required and must use letters, digits, _, . or -")
    if not _NAME_RE.fullmatch(account):
        errors.append("account is required and must use letters, digits, _, . or -")
    if request.nodes.strip() != "1":
        errors.append("this draft supports exactly one node (multi-node Fluent launch is not generated)")

    cpus = _cpus(request.cpus_per_task, errors)
    walltime = _walltime(request.walltime, errors)

    version = request.fluent_version.strip()
    if not _VERSION_RE.fullmatch(version):
        errors.append("Fluent version must look like 25.2")
    dimension = request.dimension.strip().lower()
    precision = request.precision.strip().lower()
    if dimension not in ("2d", "3d"):
        errors.append("dimension must be 2d or 3d")
    if precision not in ("sp", "dp"):
        errors.append("precision must be sp or dp")

    if errors:
        raise SlurmDraftError(errors)

    script_name = f"{job_name}_draft.slurm"
    return ResolvedDraft(
        job_name=job_name,
        partition=partition,
        account=account,
        cpus_per_task=cpus,
        walltime=walltime,
        workdir=workdir,
        journal_path=journal,
        journal_remote_path=str(PurePosixPath(workdir) / journal),
        fluent_bin_dir="v" + version.replace(".", ""),
        fluent_mode=f"{dimension}{precision}",
        script_name=script_name,
        script_path=str(PurePosixPath(workdir) / script_name),
    )
