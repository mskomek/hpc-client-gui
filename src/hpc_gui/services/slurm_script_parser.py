from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass
from typing import Optional, Tuple

SBATCH_OUT_PATTERNS = [
    # Slurm accepts both ``--output=file`` and ``--output file``.  The
    # latter was previously ignored, leaving the post-sbatch follower with
    # no output path to open.
    re.compile(r"^\s*#SBATCH\s+--output(?:\s*=\s*|\s+)(.+?)\s*$"),
    re.compile(r"^\s*#SBATCH\s+-o(?:\s+|(?=\S))(.+?)\s*$"),
]
SBATCH_ERR_PATTERNS = [
    # Keep error handling symmetrical with output handling; compact short
    # options such as ``-ejob.err`` are also valid Slurm syntax.
    re.compile(r"^\s*#SBATCH\s+--error(?:\s*=\s*|\s+)(.+?)\s*$"),
    re.compile(r"^\s*#SBATCH\s+-e(?:\s+|(?=\S))(.+?)\s*$"),
]
SBATCH_JOB_NAME_PATTERNS = [
    re.compile(r"^\s*#SBATCH\s+--job-name\s*=\s*(.+?)\s*$"),
    re.compile(r"^\s*#SBATCH\s+--job-name\s+(.+?)\s*$"),
    re.compile(r"^\s*#SBATCH\s+-J\s+(.+?)\s*$"),
    re.compile(r"^\s*#SBATCH\s+-J([^\s].*?)\s*$"),
]
SBATCH_CHDIR_PATTERNS = [
    re.compile(r"^\s*#SBATCH\s+--chdir\s*=\s*(.+?)\s*$"),
    re.compile(r"^\s*#SBATCH\s+--chdir\s+(.+?)\s*$"),
    re.compile(r"^\s*#SBATCH\s+-D\s+(.+?)\s*$"),
    re.compile(r"^\s*#SBATCH\s+-D([^\s].*?)\s*$"),
]


@dataclass(frozen=True)
class SlurmJobPaths:
    workdir: str
    stdout: str
    stderr: str


def _directive_lines(script_text: str) -> list[str]:
    """Return only directives before the script's first executable line."""
    result = []
    for line in script_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            if stripped.startswith("#SBATCH"):
                result.append(line)
            continue
        break
    return result

def _first_match(lines, patterns) -> Optional[str]:
    for ln in lines:
        for pat in patterns:
            m = pat.match(ln)
            if m:
                return m.group(1).strip().strip('"').strip("'")
    return None

def parse_output_error(script_text: str) -> Tuple[Optional[str], Optional[str]]:
    lines = _directive_lines(script_text)
    out = _first_match(lines, SBATCH_OUT_PATTERNS)
    err = _first_match(lines, SBATCH_ERR_PATTERNS)
    return out, err

def parse_job_name(script_text: str) -> Optional[str]:
    return _first_match(_directive_lines(script_text), SBATCH_JOB_NAME_PATTERNS)


def parse_job_paths(
    script_text: str,
    script_remote_path: str,
    job_id: Optional[str] = None,
    job_name: Optional[str] = None,
    submission_dir: Optional[str] = None,
) -> SlurmJobPaths:
    """Resolve Slurm work/output paths without executing or expanding a script.

    ``submission_dir`` is the actual ``sbatch`` working directory when known;
    the script directory preserves the application's existing submission flow.
    """
    base = submission_dir or posixpath.dirname(script_remote_path) or "."
    chdir = _first_match(_directive_lines(script_text), SBATCH_CHDIR_PATTERNS)
    workdir = _resolve_from_dir(base, chdir) if chdir else base
    out_raw, err_raw = parse_output_error(script_text)
    out_raw = out_raw or "slurm-%j.out"
    err_raw = err_raw or out_raw
    return SlurmJobPaths(
        workdir=workdir,
        stdout=_resolve_from_dir(workdir, out_raw, job_id, job_name),
        stderr=_resolve_from_dir(workdir, err_raw, job_id, job_name),
    )


def _resolve_from_dir(
    directory: str,
    value: str,
    job_id: Optional[str] = None,
    job_name: Optional[str] = None,
) -> str:
    if job_id:
        job_id = str(job_id)
        master_id, _, array_id = job_id.partition("_")
        value = value.replace("%j", job_id).replace("%J", job_id)
        value = value.replace("%A", master_id)
        if array_id:
            value = value.replace("%a", array_id)
    if job_name:
        value = value.replace("%x", str(job_name))
    return posixpath.normpath(value if value.startswith("/") else posixpath.join(directory, value))


def storage_area_for_path(path: str, roots: dict[str, str]) -> Optional[str]:
    """Return the most specific known storage root containing ``path``."""
    candidate = posixpath.normpath(path)
    matches = []
    for name, root in roots.items():
        root = str(root or "").strip()
        if not root.startswith("/"):
            continue
        root = posixpath.normpath(root)
        try:
            if posixpath.commonpath((candidate, root)) == root:
                matches.append((len(root), name))
        except ValueError:
            continue
    return max(matches)[1] if matches else None

def resolve_path(script_remote_path: str, value: str, job_id: Optional[str] = None, job_name: Optional[str] = None) -> str:
    # Replace common placeholders if possible
    if job_id:
        value = value.replace("%j", str(job_id)).replace("%A", str(job_id))
    if job_name:
        value = value.replace("%x", str(job_name))
    # If relative, resolve relative to script directory
    if not value.startswith("/"):
        base = posixpath.dirname(script_remote_path)
        value = posixpath.join(base, value)
    return value
