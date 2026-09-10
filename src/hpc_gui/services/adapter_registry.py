"""Framework-neutral adapter registry for Wave 79.

Adapters are application-owned trusted command constructors. Provider/plugin
configs select adapter IDs declaratively but cannot inject command text or
executable code.

Architecture:
    provider config (adapter_id)
        ↓
    adapter registry
        ↓
    trusted command construction
        ↓
    backend execution → RawCommandResult
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from hpc_gui.services.raw_command_result import RawCommandResult

log = logging.getLogger(__name__)


def _raw_response(value, *, source_id: str, command: str) -> RawCommandResult:
    if isinstance(value, RawCommandResult):
        return value
    return RawCommandResult.from_response(
        source_id=source_id,
        command=command,
        stdout=str(value or ""),
        stderr="",
        exit_code=-1,
    )


@dataclass(frozen=True)
class AdapterSpec:
    """Descriptor for a registered adapter."""

    adapter_id: str
    description: str
    # The function that constructs and executes the command.
    # Signature: (job_id: str, user: str, system_settings: dict) -> RawCommandResult
    execute: Callable[..., RawCommandResult]


# Registry of adapter_id -> AdapterSpec
_REGISTRY: dict[str, AdapterSpec] = {}


def register_adapter(adapter_id: str, execute_fn: Callable[..., RawCommandResult], description: str = "") -> None:
    """Register an adapter function under a stable ID."""
    if not isinstance(adapter_id, str) or not adapter_id.strip():
        raise ValueError("adapter_id must be a non-empty string")
    if not callable(execute_fn):
        raise TypeError("execute_fn must be callable")
    _REGISTRY[adapter_id] = AdapterSpec(
        adapter_id=adapter_id,
        description=description,
        execute=execute_fn,
    )


def get_adapter(adapter_id: str) -> AdapterSpec | None:
    """Look up a registered adapter by ID."""
    return _REGISTRY.get(adapter_id)


def known_adapter_ids() -> frozenset[str]:
    """Return all registered adapter IDs."""
    return frozenset(_REGISTRY.keys())


def clear_registry() -> None:
    """Reset registry — for testing only."""
    _REGISTRY.clear()


# ---------------------------------------------------------------------------
# Built-in Slurm adapters — registered at import time
# ---------------------------------------------------------------------------

def _adapter_scontrol_job(slurm_backend, job_id: str = "", **_kwargs) -> RawCommandResult:
    """Adapter for scontrol show job."""
    try:
        result = slurm_backend.scontrol_show_job(job_id)
        return _raw_response(result, source_id="scontrol", command=f"scontrol show job {job_id}")
    except Exception as exc:
        return RawCommandResult.from_response(
            source_id="scontrol",
            command=f"scontrol show job {job_id}",
            stdout="", stderr=str(exc), exit_code=1,
        )


def _adapter_sacct_job(slurm_backend, job_id: str = "", user: str = "", **_kwargs) -> RawCommandResult:
    """Adapter for sacct per-job query."""
    try:
        sacct_job = getattr(slurm_backend, "sacct_job", None)
        if callable(sacct_job):
            result = sacct_job(job_id)
        else:
            try:
                result = slurm_backend.sacct(user, job_id=job_id)
            except TypeError:
                result = slurm_backend.sacct(user)
        return _raw_response(
            result,
            source_id="sacct",
            command=f"sacct -n -P -j {job_id} --format=JobIDRaw,State,Elapsed,MaxRSS,AllocTRES,ExitCode",
        )
    except Exception as exc:
        return RawCommandResult.from_response(
            source_id="sacct",
            command=f"sacct -n -P -j {job_id}",
            stdout="", stderr=str(exc), exit_code=1,
        )


def _adapter_lssrv(slurm_backend, **_kwargs) -> RawCommandResult:
    """Adapter for lssrv cluster status."""
    try:
        result = slurm_backend.lssrv()
        return _raw_response(result, source_id="lssrv", command="lssrv")
    except Exception as exc:
        return RawCommandResult.from_response(
            source_id="lssrv",
            command="lssrv",
            stdout="", stderr=str(exc), exit_code=1,
        )


# Register built-in adapters
register_adapter("slurm.scontrol.job", _adapter_scontrol_job, "Slurm scontrol show job")
register_adapter("slurm.sacct.job", _adapter_sacct_job, "Slurm sacct per-job query")
register_adapter("truba.lssrv", _adapter_lssrv, "TRUBA lssrv cluster status")
