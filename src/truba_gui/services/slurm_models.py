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


def _rows(text: str) -> list[tuple[str, list[str]]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    header = lines[0]
    delimiter = "|" if "|" in header else None
    return [(line, [part.strip() for part in line.split(delimiter)]) for line in lines[1:]]


def parse_squeue(text: str) -> list[SlurmJob]:
    jobs = []
    for raw, fields in _rows(text):
        if len(fields) < 6 or fields[0].lower() == "jobid":
            continue
        if len(fields) >= 9:
            job_id, partition, name, user, state, elapsed = fields[:6]
        else:
            job_id, partition, name, user, state, elapsed = (fields + [""] * 6)[:6]
        jobs.append(SlurmJob(job_id, name, user, state, elapsed, partition=partition, raw=raw))
    return jobs


def parse_sacct(text: str) -> list[SlurmJob]:
    jobs = []
    for raw, fields in _rows(text):
        if len(fields) < 3 or fields[0].lower() == "jobid":
            continue
        fields += [""] * (5 - len(fields))
        job_id, name, state, elapsed, max_rss = fields[:5]
        jobs.append(SlurmJob(job_id, name, state=state, elapsed=elapsed, max_rss=max_rss, raw=raw))
    return jobs
