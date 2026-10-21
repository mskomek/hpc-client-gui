"""Composition facade for wx shell Jobs workflows."""

from __future__ import annotations

from hpc_gui.wx_shell_files import _remote_files_callbacks
from hpc_gui.wx_shell_jobs_context import JobsCallbackContext
from hpc_gui.wx_shell_jobs_details import make_details_callbacks
from hpc_gui.wx_shell_jobs_files import make_file_callbacks
from hpc_gui.wx_shell_jobs_history import make_history_callbacks
from hpc_gui.wx_shell_jobs_persistence import make_persistence_callbacks


def _jobs_callbacks(session_state, parent, lifecycle):
    """Compose Jobs service callbacks while preserving the existing contract."""
    context = JobsCallbackContext(session_state, parent, lifecycle)
    callbacks = {}
    callbacks.update(make_history_callbacks(context))
    callbacks.update(make_details_callbacks(context))
    callbacks.update(make_file_callbacks(context))
    callbacks.update(make_persistence_callbacks(context))
    callbacks.update(
        {
            "provider_filters": lambda: _provider_filters(context),
            "remote_files_callbacks": _remote_files_callbacks(session_state, parent, lifecycle),
            "generation": lambda: context.state.get("generation", 0),
            **context.profile_identity(),
            "lifecycle": lifecycle,
            "session_state": session_state,
        }
    )
    return callbacks


def _provider_filters(context):
    filters = context.resolve_provider_config().get("file_filters", ())
    return filters if isinstance(filters, (list, tuple)) else ()
