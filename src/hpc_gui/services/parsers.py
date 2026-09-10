"""Application-owned parsers for Wave 79.

Parser IDs:
    - slurm.scontrol.v1   — scontrol show job output
    - slurm.sacct.pipe.v1 — pipe-delimited sacct output
    - truba.lssrv.v1      — TRUBA lssrv cluster status output

Each parser is a pure function: (raw_text, parser_config) -> parsed model.
Parser exceptions become ParseError via the registry wrapper.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from hpc_gui.services.cluster_server_status import ClusterServerStatus
from hpc_gui.services.parser_registry import register_parser


# ---------------------------------------------------------------------------
# slurm.scontrol.v1
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScontrolJobDetails:
    """Normalized model for scontrol show job output."""

    job_id: str = ""
    name: str = ""
    state: str = ""
    partition: str = ""
    elapsed: str = ""
    nodes: str = ""
    cpus: str = ""
    reason: str = ""
    workdir: str = ""
    stdout_path: str = ""
    stderr_path: str = ""
    script_path: str = ""
    nodelist: str = ""
    exit_code: str = ""
    user: str = ""
    raw: str = ""
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})


_KNOWN_SCONTROL_KEYS = frozenset({
    "JobId", "JobName", "UserId", "Group", "MCS_label", "Priority",
    "Nice", "Account", "QOS", "JobState", "Reason", "Dependency",
    "Requeue", "Restarts", "RunTime", "TimeLimit", "TimeMin",
    "SubmitTime", "EligibleTime", "StartTime", "EndTime", "Elapsed",
    "ExitCode", "DerivedExitCode", "Partition", "AllocNode:Sid",
    "ReqNodeList", "ExcNodeList", "NodeList", "BatchHost",
    "NumNodes", "NumCPUs", "NumTasks", "CPUs/Task", "ReqB:S:C:T",
    "Tres", "Command", "WorkDir", "StdErr", "StdIn", "StdOut",
    "Power", "Reboot", "ResizeTime", "Share", "Socks/Node",
    "BatchScript", "oom_kill_step", "Comments", "ArrayJobId",
    "ArrayTaskId", "CoreSpec", "MinCPUsNode", "MinMemoryNode",
    "MinTmpDiskNode", "Features", "DelayBoot", "OverSubscribe",
    "Contiguous", "Licenses", "Network", "Command",
})

# Keys where we extract the value for our normalized model
_KEY_MAP = {
    "JobId": "job_id",
    "JobName": "name",
    "JobState": "state",
    "Partition": "partition",
    "Elapsed": "elapsed",
    "NumNodes": "nodes",
    "NumCPUs": "cpus",
    "Reason": "reason",
    "WorkDir": "workdir",
    "StdOut": "stdout_path",
    "StdErr": "stderr_path",
    "Command": "script_path",
    "NodeList": "nodelist",
    "ExitCode": "exit_code",
    "UserId": "user",
}


def _parse_scontrol_fields(raw: str) -> dict[str, str]:
    """Extract key=value pairs from scontrol output.

    scontrol output uses "Key=Value" with possible whitespace around '='.
    Values may contain spaces if quoted. Multi-line output is joined.
    """
    fields: dict[str, str] = {}
    # Join multi-line into single line for regex extraction
    text = raw.replace("\n", " ")
    for match in re.finditer(
        r'(?P<key>[A-Za-z/]+)=(?P<value>"[^"]*"|\S+)',
        text,
    ):
        key = match.group("key")
        value = match.group("value").strip().strip('"')
        fields[key] = value
    return fields


def _parse_scontrol_v1(raw_text: str, parser_config: dict[str, Any] | None = None) -> ScontrolJobDetails:
    """Parse scontrol show job output into normalized model.

    Tolerant of:
    - field ordering
    - multi-line scontrol
    - unknown fields (ignored/preserved as metadata)
    - missing optional fields
    """
    fields = _parse_scontrol_fields(raw_text)
    if not fields:
        raise ValueError("No key=value fields found in scontrol output")

    # Extract known fields into normalized model
    normalized: dict[str, Any] = {"raw": raw_text, "metadata": {}}
    for scontrol_key, model_key in _KEY_MAP.items():
        if scontrol_key in fields:
            normalized[model_key] = fields[scontrol_key]

    # Preserve unknown fields as metadata
    for key, value in fields.items():
        if key not in _KNOWN_SCONTROL_KEYS and key not in _KEY_MAP:
            normalized.setdefault("metadata", {})[key] = value

    return ScontrolJobDetails(**{k: v for k, v in normalized.items() if k in ScontrolJobDetails.__dataclass_fields__})


# ---------------------------------------------------------------------------
# slurm.sacct.pipe.v1
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SacctAccountingRow:
    """Normalized model for one sacct pipe-delimited row."""

    job_id: str = ""
    state: str = ""
    elapsed: str = ""
    max_rss: str = ""
    alloc_tres: str = ""
    exit_code: str = ""
    job_name: str = ""
    raw_row: str = ""
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})


@dataclass(frozen=True)
class SacctAccountingResult:
    """Result of parsing sacct pipe output."""

    rows: tuple[SacctAccountingRow, ...] = ()
    warnings: tuple[str, ...] = ()
    raw_text: str = ""


def _parse_sacct_pipe_v1(raw_text: str, parser_config: dict[str, Any] | None = None) -> SacctAccountingResult:
    """Parse pipe-delimited sacct output.

    Expected adapter command:
        sacct -n -P -j {job_id} --format=JobIDRaw,State,Elapsed,MaxRSS,AllocTRES,ExitCode

    Tolerant of:
    - empty fields (preserve as empty string)
    - blank lines
    - job-step rows (handled deliberately)
    - malformed lines (parse warning, other good rows preserved)
    """
    rows: list[SacctAccountingRow] = []
    warnings: list[str] = []
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    for line_num, line in enumerate(lines, 1):
        fields = [f.strip() for f in line.split("|")]
        # Skip header row: first field matches known header names
        if fields and fields[0].lower() in ("jobid", "jobidraw"):
            continue
        if len(fields) < 2:
            warnings.append(f"Line {line_num}: insufficient fields")
            continue

        # Pad to at least 6 fields
        fields += [""] * (6 - len(fields))

        job_id = fields[0]
        state = fields[1]
        elapsed = fields[2]
        max_rss = fields[3]
        alloc_tres = fields[4]
        exit_code = fields[5]

        rows.append(SacctAccountingRow(
            job_id=job_id,
            state=state,
            elapsed=elapsed,
            max_rss=max_rss,
            alloc_tres=alloc_tres,
            exit_code=exit_code,
            raw_row=line,
        ))

    return SacctAccountingResult(
        rows=tuple(rows),
        warnings=tuple(warnings),
        raw_text=raw_text,
    )


# ---------------------------------------------------------------------------
# truba.lssrv.v1
# ---------------------------------------------------------------------------

def _parse_truba_lssrv_v1(raw_text: str, parser_config: dict[str, Any] | None = None) -> list[ClusterServerStatus]:
    """Parse the human-readable table emitted by TRUBA's ``lssrv``.

    Rows are: partition, free CPUs, total CPUs, waiting jobs (resources),
    waiting jobs (total), total nodes, maximum job time, minimum/maximum nodes
    per job, cores per node, and RAM (MB) per core.
    """
    text = str(raw_text or "")
    if not text.strip():
        return []

    ansi = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
    border = re.compile(r"[┌┐└┘├┤┬┴┼─═╔╗╚╝╠╣╦╩╬┏┓┗┛┣┫┳┻╋╭╮╯╰]")
    count = re.compile(r"(?:\d+|N/?A|-)", re.IGNORECASE)
    lines = [ansi.sub("", line) for line in text.splitlines() if ansi.sub("", line).strip()]
    header = " ".join(lines[:5]).lower()
    required_header_words = ("partition", "cpus", "wait", "jobs", "nodes", "max", "job", "time", "min", "core", "ram")
    if not all(word in header for word in required_header_words):
        raise ValueError("unrecognized lssrv header")

    results: list[ClusterServerStatus] = []
    saw_row = False

    for raw_line in text.splitlines():
        line = ansi.sub("", raw_line).strip()
        if not line:
            continue

        if any(separator in line for separator in ("|", "│", "┃")):
            fields = [part.strip() for part in re.split(r"[|│┃]", line) if part.strip()]
        else:
            fields = border.sub(" ", line).split()
        if len(fields) >= 6 and fields[0].lower() not in {"partition", "name"}:
            saw_row = True
        if len(fields) == 12 and fields[-1].upper() == "MB":
            fields[10] = f"{fields[10]} MB"
            fields.pop()
        if len(fields) != 11 or not count.fullmatch(fields[1]) or not count.fullmatch(fields[2]):
            continue

        results.append(ClusterServerStatus(
            partition=fields[0],
            free_cpus=fields[1],
            total_cpus=fields[2],
            wait_jobs_resources=fields[3],
            wait_jobs_total=fields[4],
            nodes_total=fields[5],
            max_job_time=fields[6],
            min_nodes_per_job=fields[7],
            max_nodes_per_job=fields[8],
            cores_per_node=fields[9],
            memory_mb_per_core=fields[10],
            raw_row=raw_line,
        ))

    if saw_row and not results:
        raise ValueError("malformed lssrv row")
    return results


def register_builtin_parsers() -> None:
    """Register the parsers owned by the application."""
    register_parser("slurm.scontrol.v1", _parse_scontrol_v1)
    register_parser("slurm.sacct.pipe.v1", _parse_sacct_pipe_v1)
    register_parser("truba.lssrv.v1", _parse_truba_lssrv_v1)


register_builtin_parsers()
