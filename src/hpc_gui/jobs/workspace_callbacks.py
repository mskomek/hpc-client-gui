"""Backward-compatible normalization of Jobs provider callback names."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class JobsProviderCallbacks:
    refresh_accounting: Callable | None
    show_job_details: Callable | None
    refresh_cluster_status: Callable | None
    list_job_files: Callable | None


def normalize_provider_callbacks(
    *,
    refresh_accounting=None,
    show_job_details=None,
    refresh_cluster_status=None,
    list_job_files=None,
    kwargs: dict[str, Any],
) -> JobsProviderCallbacks:
    """Accept legacy adapter spellings at the UI boundary only."""
    return JobsProviderCallbacks(
        refresh_accounting=refresh_accounting or first_callable(
            kwargs, "refresh_sacct", "sacct", "sacct_callback", "refresh_accounting"
        ),
        show_job_details=show_job_details or first_callable(
            kwargs, "show_details", "scontrol", "scontrol_show_job", "show_details_callback",
            "show_job_details",
        ),
        refresh_cluster_status=refresh_cluster_status or first_callable(
            kwargs, "lssrv", "lssrv_refresh", "lssrv_callback",
            "refresh_lssrv_callback", "refresh_lssrv",
        ),
        list_job_files=list_job_files or first_callable(
            kwargs, "list_job_files", "job_files", "files_callback"
        ),
    )


def first_callable(values: dict[str, Any], *names: str):
    for name in names:
        callback = values.get(name)
        if callable(callback):
            return callback
    return None
