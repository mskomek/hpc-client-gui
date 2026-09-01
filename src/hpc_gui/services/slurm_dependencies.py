"""Conservative Slurm dependency values and directive helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from hpc_gui.services.slurm_directives import get_directive, remove_directive, set_directive


class DependencyType(str, Enum):
    AFTEROK = "afterok"
    AFTERANY = "afterany"
    AFTERNOTOK = "afternotok"
    AFTER = "after"


_JOB_ID = re.compile(r"^\d+(?:_\d+)?(?:\.\d+)?$")


@dataclass(frozen=True)
class SlurmDependency:
    kind: DependencyType
    job_ids: tuple[str, ...]
    connection_id: str | None = None

    def __post_init__(self) -> None:
        if not self.job_ids or any(not _JOB_ID.fullmatch(str(job_id)) for job_id in self.job_ids):
            raise ValueError("dependency job IDs must be numeric job or array-task IDs")
        if len(set(self.job_ids)) != len(self.job_ids):
            raise ValueError("dependency job IDs must be unique")

    def render(self) -> str:
        return f"{self.kind.value}:{','.join(self.job_ids)}"

    def directive(self) -> str:
        return f"#SBATCH --dependency={self.render()}"

    def valid_for_connection(self, connection_id: str | None) -> bool:
        return self.connection_id is None or self.connection_id == connection_id


def parse_dependency(value: str, *, connection_id: str | None = None) -> SlurmDependency:
    kind_value, separator, ids_value = str(value).strip().partition(":")
    if not separator or kind_value not in {item.value for item in DependencyType}:
        raise ValueError("dependency must use TYPE:JOB_ID[,JOB_ID...]")
    ids = tuple(part.strip() for part in ids_value.split(",") if part.strip())
    return SlurmDependency(DependencyType(kind_value), ids, connection_id)


def get_dependency(script_text: str, *, connection_id: str | None = None) -> SlurmDependency | None:
    value = get_directive(script_text, "dependency")
    return None if value in (None, "") else parse_dependency(value, connection_id=connection_id)


def set_dependency(script_text: str, dependency: SlurmDependency | str) -> str:
    if isinstance(dependency, str):
        dependency = parse_dependency(dependency)
    if not isinstance(dependency, SlurmDependency):
        raise TypeError("dependency must be SlurmDependency or a dependency expression")
    return set_directive(script_text, "dependency", dependency.render())


def remove_dependency(script_text: str) -> str:
    return remove_directive(script_text, "dependency")
