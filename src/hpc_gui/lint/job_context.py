"""Static Slurm/Fluent job-context parsing and cross-validation.

Best-effort, purely static analysis: scripts are never executed and shell
semantics are not evaluated. Unknown values stay ``None`` and checks that
cannot be decided unambiguously degrade to "skip".

No cluster-specific constants live here; verified site limits belong to
cluster plugins.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass

from hpc_gui.lint.models import Diagnostic, Severity


@dataclass(frozen=True)
class SlurmJobContext:
    scheduler: str = "slurm"
    nodes: int | None = None
    ntasks: int | None = None
    cpus_per_task: int | None = None
    memory_bytes: int | None = None
    partition: str | None = None
    constraint: str | None = None
    time_limit_seconds: int | None = None
    # True when directives the parser does not model (for example
    # --ntasks-per-node, --gpus) may change the CPU accounting.
    allocation_ambiguous: bool = False


@dataclass(frozen=True)
class FluentLaunch:
    processes: int | None = None
    headless: bool | None = None
    raw_command: str = ""


_DYNAMIC_VALUE_RE = re.compile(r"[$`\\(]")


def _parse_int(value: str) -> int | None:
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


_MEM_MULTIPLIERS = {
    "": 1,
    "K": 1024,
    "M": 1024**2,
    "G": 1024**3,
    "T": 1024**4,
}


def _parse_memory_bytes(value: str) -> int | None:
    match = re.fullmatch(r"(\d+)([KMGTP]?)[iI]?", value.strip())
    if not match:
        return None
    multiplier = _MEM_MULTIPLIERS.get(match.group(2).upper(), 0)
    if multiplier == 0:
        return None
    return int(match.group(1)) * multiplier


def _parse_time_seconds(value: str) -> int | None:
    """Accept [days-]hours:minutes[:seconds] and bare minutes."""
    value = value.strip().lower()
    days = 0
    if "-" in value:
        day_part, _, value = value.partition("-")
        if not day_part.isdigit():
            return None
        days = int(day_part)
    parts = value.split(":")
    if not all(part.isdigit() for part in parts):
        return None
    numbers = [int(part) for part in parts]
    if len(numbers) == 1:
        minutes = numbers[0]
        hours = seconds = 0
    elif len(numbers) == 2:
        hours, minutes = numbers
        seconds = 0
    elif len(numbers) == 3:
        hours, minutes, seconds = numbers
    else:
        return None
    return ((days * 24 + hours) * 60 + minutes) * 60 + seconds


SBATCH_LINE_RE = re.compile(r"^#\s*@?SBATCH\s+(.+)$", re.IGNORECASE)


def _directive_and_value(argument_text: str) -> tuple[str, str] | None:
    argument_text = argument_text.split("#", 1)[0].strip()
    if not argument_text:
        return None
    if argument_text.startswith("--"):
        if "=" in argument_text:
            key, _, value = argument_text.partition("=")
        else:
            parts = argument_text.split(None, 1)
            key = parts[0]
            value = parts[1] if len(parts) > 1 else ""
        return key.lower(), value.strip()
    match = re.match(r"^(-[A-Za-z])\s+(\S+)$", argument_text)
    if match:
        # Short flags are case-sensitive (-N nodes vs -n ntasks).
        return match.group(1), match.group(2).strip()
    return None


_SHORT_KEYS = {"-n": "ntasks", "-N": "nodes", "-c": "cpus_per_task"}

_LONG_KEYS = {
    "--nodes": "nodes",
    "--ntasks": "ntasks",
    "--cpus-per-task": "cpus_per_task",
    "--mem": "memory",
    "--partition": "partition",
    "--constraint": "constraint",
    "--time": "time",
}

_INT_FIELDS = {"nodes", "ntasks", "cpus_per_task"}

# Directives that change CPU accounting in ways this parser does not model.
_AMBIGUOUS_KEYS = {
    "--ntasks-per-node",
    "--gpus",
    "--gpus-per-task",
    "--gpus-per-node",
    "--cpus-per-gpu",
    "--exclusive",
}


def parse_slurm_context(text: str) -> SlurmJobContext | None:
    """Parse common #SBATCH directives; returns None without directives.

    Later valid occurrences override earlier ones. Dynamically generated
    values are ignored rather than guessed.
    """
    found: dict[str, str] = {}
    saw_directive = False
    allocation_ambiguous = False
    for line in text.splitlines():
        match = SBATCH_LINE_RE.match(line.strip())
        if not match:
            continue
        argument_text = match.group(1).split("#", 1)[0].strip()
        key_probe = argument_text.split("=", 1)[0].split(None, 1)[0].lower() if argument_text else ""
        if key_probe in _AMBIGUOUS_KEYS:
            allocation_ambiguous = True
        parsed = _directive_and_value(match.group(1))
        if parsed is None:
            continue
        key, value = parsed
        canonical = _LONG_KEYS.get(key) or _SHORT_KEYS.get(key)
        if canonical is None:
            continue
        saw_directive = True
        if not value or _DYNAMIC_VALUE_RE.search(value):
            # Recognized directive with an unresolvable value: keep context,
            # leave the field unknown.
            continue
        found[canonical] = value

    if not saw_directive:
        return None

    def integer(field_name: str) -> int | None:
        raw_value = found.get(field_name)
        return _parse_int(raw_value) if raw_value is not None else None

    memory_raw = found.get("memory")
    time_raw = found.get("time")
    return SlurmJobContext(
        nodes=integer("nodes"),
        ntasks=integer("ntasks"),
        cpus_per_task=integer("cpus_per_task"),
        memory_bytes=_parse_memory_bytes(memory_raw) if memory_raw else None,
        partition=found.get("partition"),
        constraint=found.get("constraint"),
        time_limit_seconds=_parse_time_seconds(time_raw) if time_raw else None,
        allocation_ambiguous=allocation_ambiguous,
    )


_FLUENT_EXECUTABLE_RE = re.compile(r"(^|[\\/])fluent(\.exe)?$", re.IGNORECASE)


def parse_fluent_launch(text: str) -> FluentLaunch | None:
    """Find a Fluent launch command in a shell script; static tokenization."""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "fluent" not in stripped.lower():
            continue
        try:
            tokens = shlex.split(stripped, comments=False, posix=True)
        except ValueError:
            continue
        for position, token in enumerate(tokens):
            basename = re.split(r"[\\/]", token)[-1]
            candidate = basename.lower()
            is_option = candidate.startswith("-")
            # Accept any path whose executable name contains "fluent" so
            # quoted install paths work without resolving shell variables.
            if "fluent" not in candidate or is_option:
                continue
            processes: int | None = None
            headless: bool | None = None
            index = position + 1
            while index < len(tokens):
                token_now = tokens[index]
                lowered = token_now.lower()
                if lowered == "-t":
                    if index + 1 < len(tokens):
                        processes = _parse_int(tokens[index + 1])
                        index += 1
                elif lowered.startswith("-t") and len(lowered) > 2:
                    processes = _parse_int(lowered[2:])
                elif lowered == "-g":
                    headless = True
                index += 1
            return FluentLaunch(processes=processes, headless=headless, raw_command=stripped)
    return None


def allocated_cpus(context: SlurmJobContext) -> int | None:
    """Total CPUs for the job step, only when unambiguous."""
    cpus = context.cpus_per_task
    if cpus is None:
        return None
    if context.allocation_ambiguous and (
        context.nodes is None or context.ntasks is None
    ):
        return None
    nodes = context.nodes if context.nodes is not None else 1
    ntasks = context.ntasks if context.ntasks is not None else 1
    return nodes * ntasks * cpus


CROSS_RULE_ID = "HPC-FLUENT-001"


def cross_diagnostics(
    context: SlurmJobContext | None, launch: FluentLaunch | None
) -> list[Diagnostic]:
    """Resource-consistency diagnostics between Slurm request and Fluent launch."""
    if context is None or launch is None or launch.processes is None:
        return []
    total = allocated_cpus(context)
    if total is None or total <= 0:
        return []
    if total == launch.processes:
        return []
    return [
        Diagnostic(
            rule_id=CROSS_RULE_ID,
            severity=Severity.WARNING,
            category="cross-check",
            message=(
                f"Slurm allocates {total} CPUs to the task, while Fluent is "
                f"launched with {launch.processes} solver processes."
            ),
            source="slurm-fluent-cross",
            explanation=(
                "The solver process count should usually match the CPUs allocated "
                "to one task. Verify whether the difference is intentional."
            ),
        )
    ]
