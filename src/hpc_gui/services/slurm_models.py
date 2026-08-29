from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SlurmJob:
    job_id: str
    name: str = ""
    user: str = ""
    state: str = ""
    elapsed: str = ""
    max_rss: str = ""
    partition: str = ""
    raw: str = ""
    nodes: str = ""
    cpus: str = ""
    reason: str = ""
    exit_code: str = ""
    nodelist: str = ""
    failure_reason: str = ""
    script_path: str = ""
    workdir: str = ""
    stdout_path: str = ""
    stderr_path: str = ""


def _observed_fields(raw: str) -> dict[str, str]:
    """Read only key=value fields actually emitted by scheduler output."""
    fields: dict[str, str] = {}
    for token in raw.replace("|", " ").split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        if key in {"NodeList", "Reason", "ExitCode", "Command", "FailedNode", "WorkDir", "StdOut", "StdErr"}:
            fields[key] = value.strip()
    return fields

def _rows(text: str) -> list[tuple[str, list[str]]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    # Banners/MOTD noise can precede scheduler output, so the delimiter is
    # detected from the whole response rather than only the first line.
    delimiter = "|" if any("|" in line for line in lines) else None
    return [(line, [part.strip() for part in line.split(delimiter)]) for line in lines[1:]]


def parse_squeue(text: str) -> list[SlurmJob]:
    jobs = []
    for raw, fields in _rows(text):
        if len(fields) < 6 or fields[0].lower() == "jobid":
            continue
        job_id, partition, name, user, state, elapsed = (fields + [""] * 6)[:6]
        nodes = fields[6] if len(fields) > 6 else ""
        if len(fields) >= 9:
            cpus, reason = fields[7], fields[8]
        else:
            cpus, reason = "", fields[7] if len(fields) > 7 else ""
        observed = _observed_fields(raw)
        jobs.append(SlurmJob(job_id, name, user, state, elapsed, partition=partition, raw=raw, nodes=nodes, cpus=cpus, reason=reason, nodelist=observed.get("NodeList", ""), failure_reason=observed.get("Reason", ""), exit_code=observed.get("ExitCode", ""), script_path=observed.get("Command", "")))
    return jobs


def parse_sacct(text: str) -> list[SlurmJob]:
    jobs = []
    for raw, fields in _rows(text):
        if len(fields) < 3 or fields[0].lower() == "jobid":
            continue
        fields += [""] * (5 - len(fields))
        job_id, name, state, elapsed, max_rss = fields[:5]
        observed = _observed_fields(raw)
        jobs.append(SlurmJob(job_id, name, state=state, elapsed=elapsed, max_rss=max_rss, raw=raw, exit_code=observed.get("ExitCode", fields[5] if len(fields) > 5 else ""), nodelist=observed.get("NodeList", fields[6] if len(fields) > 6 else ""), failure_reason=observed.get("Reason", fields[7] if len(fields) > 7 else ""), script_path=observed.get("Command", fields[8] if len(fields) > 8 else "")))
    return jobs


def format_job_details(job: SlurmJob) -> str:
    """Return only populated structured scheduler fields for the detail view."""
    fields = (
        ("Job ID", job.job_id),
        ("Node list", job.nodelist or job.nodes),
        ("CPUs", job.cpus),
        ("Failure reason", job.failure_reason or job.reason),
        ("Exit code", job.exit_code),
        ("Script path", job.script_path),
        ("Working directory", job.workdir),
        ("Stdout path", job.stdout_path),
        ("Stderr path", job.stderr_path),
    )
    return "\n".join(f"{label}: {value}" for label, value in fields if value)

def parse_scontrol(text: str, job_id: str = "") -> SlurmJob:
    """Parse observed key=value fields from one scontrol detail response."""
    observed = _observed_fields(text.replace("\n", " "))
    return SlurmJob(
        job_id=job_id,
        raw=text,
        nodelist=observed.get("NodeList", ""),
        failure_reason=observed.get("Reason", ""),
        exit_code=observed.get("ExitCode", ""),
        script_path=observed.get("Command", ""),
        workdir=observed.get("WorkDir", ""),
        stdout_path=observed.get("StdOut", ""),
        stderr_path=observed.get("StdErr", ""),
    )
