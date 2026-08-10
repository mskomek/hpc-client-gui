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

def _first_match(lines, patterns) -> Optional[str]:
    for ln in lines:
        for pat in patterns:
            m = pat.match(ln)
            if m:
                return m.group(1).strip().strip('"').strip("'")
    return None

def parse_output_error(script_text: str) -> Tuple[Optional[str], Optional[str]]:
    lines = script_text.splitlines()
    out = _first_match(lines, SBATCH_OUT_PATTERNS)
    err = _first_match(lines, SBATCH_ERR_PATTERNS)
    return out, err

def parse_job_name(script_text: str) -> Optional[str]:
    return _first_match(script_text.splitlines(), SBATCH_JOB_NAME_PATTERNS)

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
