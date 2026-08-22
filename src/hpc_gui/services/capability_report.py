"""Capability contract for SSH+Slurm environments.

The report expresses what an environment supports independently of any site:
each capability is ``available``, ``unavailable``, or ``unknown``. Building the
report is pure — callers decide how the probe values were obtained, and no
state-changing command is implied.
"""

from __future__ import annotations

from typing import Mapping

from dataclasses import dataclass, field

CAPABILITY_KEYS = (
    "ssh_connected",
    "sftp_available",
    "slurm_squeue_available",
    "slurm_sbatch_available",
    "slurm_scancel_available",
    "slurm_sacct_available",
    "slurm_scontrol_available",
    "home_path_known",
    "scratch_path_known",
    "x11_possible",
)

_AVAILABLE = "available"
_UNAVAILABLE = "unavailable"
_UNKNOWN = "unknown"


@dataclass(frozen=True)
class CapabilityReport:
    release: str
    statuses: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_probes(
        cls,
        probes: Mapping[str, bool | None],
        *,
        release: str = "",
    ) -> "CapabilityReport":
        """Map raw boolean/None probe results into the stable status contract.

        Keys outside :data:`CAPABILITY_KEYS` are ignored so callers can pass
        wider probe dictionaries safely.
        """
        statuses = {
            key: _status(probes.get(key))
            for key in CAPABILITY_KEYS
        }
        return cls(release=release, statuses=statuses)

    def unavailable(self) -> tuple[str, ...]:
        return tuple(key for key, value in self.statuses.items() if value == _UNAVAILABLE)

    def unknown(self) -> tuple[str, ...]:
        return tuple(key for key, value in self.statuses.items() if value == _UNKNOWN)

    def as_dict(self) -> dict:
        return {"release": self.release, "capabilities": dict(self.statuses)}

    def summary(self) -> str:
        missing = self.unavailable() + self.unknown()
        if not missing:
            return f"{self.release or 'environment'}: all {len(CAPABILITY_KEYS)} capabilities available"
        return (
            f"{self.release or 'environment'}: "
            f"{len(CAPABILITY_KEYS) - len(missing)}/{len(CAPABILITY_KEYS)} available;"
            f" check {', '.join(missing)}"
        )


def _status(value: bool | None) -> str:
    if value is None:
        return _UNKNOWN
    return _AVAILABLE if value else _UNAVAILABLE
