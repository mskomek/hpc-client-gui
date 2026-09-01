"""Validated Slurm job-array values and directive integration."""

from __future__ import annotations

import re
from dataclasses import dataclass

from hpc_gui.services.slurm_directives import get_directive, remove_directive, set_directive


_ARRAY_RE = re.compile(r"^(\d+)-(\d+)(?::(\d+))?(?:%(\d+))?$")
MAX_ARRAY_SPAN = 1_000_000
MAX_CONCURRENT = 1_000_000


@dataclass(frozen=True)
class SlurmArraySpec:
    start: int
    end: int
    step: int = 1
    max_concurrent: int | None = None

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < 0 or self.start > self.end:
            raise ValueError("array range must be non-negative and start <= end")
        if self.step <= 0 or self.max_concurrent is not None and self.max_concurrent <= 0:
            raise ValueError("array step and concurrency must be positive")
        if self.max_concurrent is not None and self.max_concurrent > MAX_CONCURRENT:
            raise ValueError("array concurrency is excessive")
        if self.end - self.start + 1 > MAX_ARRAY_SPAN:
            raise ValueError("array range is excessive")

    def render(self) -> str:
        value = f"{self.start}-{self.end}"
        if self.step != 1:
            value += f":{self.step}"
        if self.max_concurrent is not None:
            value += f"%{self.max_concurrent}"
        return value

    def directive(self) -> str:
        return f"#SBATCH --array={self.render()}"


def parse_array(value: str) -> SlurmArraySpec:
    match = _ARRAY_RE.fullmatch(str(value).strip())
    if not match:
        raise ValueError("array must use START-END[:STEP][%MAX_CONCURRENT]")
    start, end, step, maximum = (int(part) if part is not None else None for part in match.groups())
    return SlurmArraySpec(start, end, step if step is not None else 1, maximum)


def get_array(script_text: str) -> SlurmArraySpec | None:
    value = get_directive(script_text, "array")
    return None if value in (None, "") else parse_array(value)


def set_array(script_text: str, spec: SlurmArraySpec | str) -> str:
    if isinstance(spec, str):
        spec = parse_array(spec)
    if not isinstance(spec, SlurmArraySpec):
        raise TypeError("spec must be SlurmArraySpec or an array expression")
    return set_directive(script_text, "array", spec.render())


def remove_array(script_text: str) -> str:
    return remove_directive(script_text, "array")


def apply_array_mode(script_text: str, enabled: bool, spec: SlurmArraySpec | str | None = None) -> str:
    """Apply the conditional Single/Array mode without touching script body."""
    if not enabled:
        return remove_array(script_text)
    if spec is None:
        raise ValueError("array specification is required in Array mode")
    return set_array(script_text, spec)
