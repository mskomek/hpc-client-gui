"""Initial mutable state for a single Jobs workspace instance."""

from __future__ import annotations

from typing import Any

from hpc_gui.services.jobs_refresh_state import JobsRefreshState


def create_workspace_state(output_channel_defs, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Create state that is never shared between workspace windows or profiles."""
    session_state = kwargs.get("session_state")
    supplied_session = isinstance(session_state, dict)
    return {
        "items": [],
        "raw_items": [],
        "selected_job": "",
        "bulk_selected_job_ids": set(),
        "rendering_jobs": False,
        "selected_generation": 0,
        "closed": False,
        "files_browser_closed": False,
        "in_flight": False,
        "refresh_pending": False,
        "output_in_flight": False,
        "cancel_in_flight": False,
        "cancel_capability": "available",
        "last_cancel_outcome": "",
        "last_cancel_message": "",
        "last_cancel_is_error": False,
        "user_paused": False,
        "minimized": False,
        "follow_calls": 0,
        "sacct_in_flight": False,
        "details_in_flight": False,
        "sacct_requests": 0,
        "details_requests": 0,
        "sacct_request_id": 0,
        "details_request_id": 0,
        "status_request_id": 0,
        "status_in_flight": False,
        "provider_generation": 0,
        "outputs_in_flight": False,
        "outputs_requests": 0,
        "outputs_request_id": 0,
        "outputs_generation": 0,
        "outputs_active_generations": set(),
        "outputs_pending_generations": {},
        "outputs_paused": False,
        "_timer_paused": False,
        "raw_scontrol_visible": False,
        "filter_query": "",
        "sort_key": "",
        "sort_reverse": False,
        "jobs_refresh": JobsRefreshState(),
        "jobs_refresh_seq": 0,
        "jobs_refresh_applied_seq": 0,
        "jobs_refresh_status": "idle",
        "jobs_refresh_timestamp": "",
        "jobs_refresh_error": "",
        "jobs_refresh_stale": False,
        "resolved_channels": [],
        "output_channel_defs": (
            list(output_channel_defs) if output_channel_defs is not None else None
        ),
        "output_channel_defs_provider": kwargs.get("output_channel_defs_provider"),
        "tracked_outputs": [],
        "followers": {},
        "detached_followers": [],
        "session": session_state.get("session") if supplied_session else None,
        "raw_details_result": None,
        "raw_accounting_result": None,
        "raw_status_result": None,
        "details_parse_error": "",
        "accounting_parse_error": "",
        "status_parse_error": "",
        "cluster_status_key": "jobs_outputs.no_cluster_connection",
        "accounting_collapsed": True,
        "advanced_collapsed": True,
        "session_state_supplied": supplied_session,
    }
