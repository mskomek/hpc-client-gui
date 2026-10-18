from __future__ import annotations

import re
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
    keys = "NodeList|Reason|ExitCode|Command|FailedNode|WorkDir|StdOut|StdErr"
    for match in re.finditer(rf"(?P<key>{keys})=(?P<value>.*?)(?=\s+\w+=|$)", raw):
        fields[match.group("key")] = match.group("value").strip().strip('"')
    return fields

def _looks_like_job_id(value: str) -> bool:
    """True when the leading field resembles a scheduler job ID.

    Structured scheduler formats always lead with the ID (``4``,
    ``123.batch``, ``123_4``), which always contains a digit. Human
    error/display text (``slurm_load_jobs error: ...``) never does, so it
    must not become a phantom job row.
    """
    return any(char.isascii() and char.isdigit() for char in value)


def _rows(text: str) -> list[tuple[str, list[str]]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    # Banners/MOTD noise can precede scheduler output, so the delimiter is
    # detected from the whole response rather than only the first line.
    delimiter = "|" if any("|" in line for line in lines) else None

    header_index = next(
        (index for index, line in enumerate(lines) if line.split()[0].lower() == "jobid"),
        None,
    )
    header_size = len(lines[header_index].split()) if header_index is not None else 0

    def _parts(line: str) -> list[str]:
        if delimiter:
            return [part.strip() for part in line.split(delimiter)]
        if header_size > 1:
            # Human-readable Slurm tables have no delimiter. Keep the final
            # NODELIST(REASON) column intact because reasons can contain spaces.
            return line.split(None, maxsplit=header_size - 1)
        return line.split()

    def _is_header(line: str) -> bool:
        fields = _parts(line)
        return bool(fields) and fields[0].lower() == "jobid"

    # The shipped scheduler commands request headerless output (``squeue -h``,
    # ``sacct -n -P``), so the first line is data unless it is a header row.
    # A single banner/MOTD line ahead of the header is still tolerated.
    # Previously the first line was always dropped, which silently discarded
    # the only (or first) real job row of every headerless response.
    start = (header_index + 1) if header_index is not None else 0
    return [(line, _parts(line)) for line in lines[start:] if not _is_header(line)]


def parse_squeue(text: str) -> list[SlurmJob]:
    jobs = []
    for raw, fields in _rows(text):
        if len(fields) < 6 or fields[0].lower() == "jobid":
            continue
        if not _looks_like_job_id(fields[0]):
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
        if not _looks_like_job_id(fields[0]):
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


# --- W28 parser safety helpers (additive; existing parsers unchanged) --------

KNOWN_SQUEUE_STATES = frozenset(
    {
        "PD", "R", "CA", "CG", "CD", "CF", "F", "NF", "PR", "RV", "S", "ST",
        "TO", "OOM",
    }
)

KNOWN_SACCT_STATES = frozenset(
    {
        "PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", "TIMEOUT",
        "OUT_OF_MEMORY", "SUSPENDED", "PREEMPTED", "NODE_FAIL", "DEADLINE",
    }
)

TERMINAL_STATES = frozenset(
    {
        "COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY",
        "PREEMPTED", "NODE_FAIL", "DEADLINE", "REVOKED", "BOOT_FAIL",
        "SPECIAL_EXIT", "STOPPED", "CD", "F", "CA", "TO", "OOM",
        "PR", "NF", "DL", "BF", "SE",
    }
)

ACTIVE_STATES = frozenset({
    "PENDING", "PD", "RUNNING", "R", "CONFIGURING", "CF", "COMPLETING", "CG",
    "SUSPENDED", "S", "RESIZING", "SIGNALING", "STAGE_OUT", "REQUEUED",
})


def safe_state_display(state: str) -> str:
    """Return a crash-safe display state; unknown/new states pass through.

    Unknown scheduler states must display safely rather than crashing or
    being misreported as success. This helper never maps an unknown token to
    a success/terminal display value.
    """
    text = str(state or "").strip()
    if not text:
        return "UNKNOWN"
    return text


def is_terminal_state(state: str) -> bool:
    """True for scheduler states that mean the job has finished."""
    text = str(state or "").strip().upper().split()[0] if str(state or "").strip() else ""
    return text.rstrip("+") in TERMINAL_STATES


def is_active_state(state: str) -> bool:
    """True only for known states where cancelling the job is appropriate."""
    text = str(state or "").strip().upper().split()[0] if str(state or "").strip() else ""
    return text.rstrip("+") in ACTIVE_STATES


def parse_squeue_result(result) -> list[SlurmJob]:
    """Parse an squeue command result without mistaking failure for empty.

    A non-zero scheduler exit (``SlurmCommandResult.ok is False``) yields no
    rows so the caller can surface the attached ``message`` instead of
    rendering error text as phantom jobs. Plain-string input keeps the legacy
    tolerant behaviour.
    """
    code = getattr(result, "code", None)
    ok = getattr(result, "ok", None)
    if code is not None or ok is not None:
        if callable(ok):
            is_ok = bool(ok())
        else:
            is_ok = bool(ok) if ok is not None else int(code) == 0
        if not is_ok:
            return []
        text = getattr(result, "stdout", None)
        if text is None:
            text = getattr(result, "text", "")
        return parse_squeue(str(text or ""))
    return parse_squeue(str(result or ""))


def parse_sacct_result(result) -> list[SlurmJob]:
    """Parse an sacct command result without mistaking failure for empty."""
    code = getattr(result, "code", None)
    ok = getattr(result, "ok", None)
    if code is not None or ok is not None:
        if callable(ok):
            is_ok = bool(ok())
        else:
            is_ok = bool(ok) if ok is not None else int(code) == 0
        if not is_ok:
            return []
        text = getattr(result, "stdout", None)
        if text is None:
            text = getattr(result, "text", "")
        return parse_sacct(str(text or ""))
    return parse_sacct(str(result or ""))
