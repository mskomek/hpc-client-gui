"""Framework-neutral Slurm job identity for W28.

Owns HPC-W07-JOB-001..004: the job identity tuple must never mix a bare
numeric job ID across profile/cluster/provider, session generations, or
array/task identifiers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


_ARRAY_SUFFIX_RE = re.compile(
    r"^(?P<base>\d+)"
    r"(?P<array>(?:_\d+|\.batch|\.extern|\[[^\]]+\])?)"
    r"(?P<step>(?:\.0|\+0|s\d+)?)$"
)


def split_job_id(raw: str) -> tuple[str, str, str]:
    """Split ``raw`` into (base_id, array_suffix, step_suffix).

    Preserves scheduler array representations such as ``123_4``,
    ``123.batch``, ``123_[1-3]`` without normalising them away. A bare
    ``123`` yields ``("123", "", "")``.
    """
    text = str(raw or "").strip()
    match = _ARRAY_SUFFIX_RE.match(text)
    if not match:
        return text, "", ""
    return match.group("base"), match.group("array"), match.group("step")


def base_job_id(raw: str) -> str:
    """Return the numeric base of a scheduler job ID."""
    base, _, _ = split_job_id(raw)
    return base


@dataclass(frozen=True)
class JobIdentity:
    """Immutable identity tuple for one selectable job row.

    ``job_id`` keeps the exact scheduler rendering (including array/task
    suffixes). ``profile_id``/``cluster_id``/``provider_id`` scope the row to
    one backend; ``session_generation`` scopes it to one connection session.
    Two identities refer to the same live target only when every field
    matches.
    """

    job_id: str
    profile_id: str = ""
    cluster_id: str = ""
    provider_id: str = ""
    session_generation: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "job_id", str(self.job_id or "").strip())
        object.__setattr__(self, "profile_id", str(self.profile_id or "").strip())
        object.__setattr__(self, "cluster_id", str(self.cluster_id or "").strip())
        object.__setattr__(self, "provider_id", str(self.provider_id or "").strip())
        object.__setattr__(self, "session_generation", int(self.session_generation or 0))

    @property
    def has_selection(self) -> bool:
        return bool(self.job_id)

    @property
    def array_parts(self) -> tuple[str, str, str]:
        return split_job_id(self.job_id)

    def same_target(self, other: "JobIdentity") -> bool:
        """True only when every identity field matches exactly."""
        if not isinstance(other, JobIdentity):
            return False
        return (
            self.job_id == other.job_id
            and self.profile_id == other.profile_id
            and self.cluster_id == other.cluster_id
            and self.provider_id == other.provider_id
            and int(self.session_generation) == int(other.session_generation)
        )


def make_identity(
    job_id: str,
    *,
    profile_id: str = "",
    cluster_id: str = "",
    provider_id: str = "",
    session_generation: int = 0,
) -> JobIdentity:
    """Build a :class:`JobIdentity` from row + session scope fields."""
    return JobIdentity(
        job_id=str(job_id or "").strip(),
        profile_id=str(profile_id or "").strip(),
        cluster_id=str(cluster_id or "").strip(),
        provider_id=str(provider_id or "").strip(),
        session_generation=int(session_generation or 0),
    )


def cancel_is_safe(selected: JobIdentity, requested: JobIdentity) -> bool:
    """Cancel gate: the requested target must equal the selected identity.

    A stale selection (profile/cluster/provider/session drift, or array/task
    suffix change) must never cancel a different row. Empty selections are
    never safe.
    """
    if not selected.has_selection or not requested.has_selection:
        return False
    return selected.same_target(requested)


def selection_survives_refresh(
    selected: JobIdentity,
    rows: list[JobIdentity],
) -> bool:
    """Selection survives a refresh only when the full identity still exists."""
    if not selected.has_selection:
        return False
    return any(selected.same_target(row) for row in rows)
