"""Stable readback hooks used by GUI acceptance and regression tests."""

from __future__ import annotations

from typing import Any


def expose_workspace_access(
    host: Any,
    *,
    model: Any,
    state: dict[str, Any],
    views: Any,
    callbacks: dict[str, Any],
) -> None:
    """Attach the established Jobs test seam without coupling tests to locals."""
    host._wx_jobs_state = state
    host._wx_jobs_model = model
    host._wx_jobs_controls = _controls(views, callbacks)
    host._wx_jobs_open_detached_output = callbacks["open_detached_output"]
    host._wx_jobs_refresh_jobs = callbacks["refresh_jobs"]
    host._wx_jobs_cancel = callbacks["cancel_job"]
    host._wx_jobs_refresh_outputs = callbacks["refresh_outputs"]
    host._wx_jobs_refresh_sacct = callbacks["refresh_accounting"]
    host._wx_jobs_refresh_raw_job_details = callbacks["refresh_raw_job_details"]
    host._wx_jobs_refresh_raw_accounting = callbacks["refresh_raw_accounting"]
    host._wx_jobs_refresh_raw_server_status = callbacks["refresh_raw_server_status"]
    host._wx_jobs_show_details = callbacks["show_job_details"]
    host._wx_jobs_notebook = views.notebook
    host._wx_jobs_navigate_files = callbacks["navigate_files"]
    host._wx_jobs_refresh_outputs_tab = callbacks["refresh_outputs_tab"]
    host._wx_jobs_set_session = callbacks["set_session"]


def _controls(views, callbacks) -> dict[str, Any]:
    jobs, cluster = views.jobs, views.cluster
    details, files, outputs = views.details, views.files, views.outputs
    return {
        "jobs": jobs.table,
        "follow": outputs.follow,
        "pause": outputs.pause,
        "refresh": jobs.refresh,
        "cancel": jobs.cancel,
        "notebook": views.notebook,
        "jobs_page": jobs.page,
        "cluster_page": cluster.page,
        "details_page": details.page,
        "files_page": files.page,
        "outputs_page": outputs.page,
        "accounting_table": details.accounting_table,
        "detail_values": details.values,
        "detail_labels": details.labels,
        "details_content_panel": details.content_panel,
        "no_selection_panel": details.no_selection_panel,
        "details_warning": details.warning,
        "collapse_accounting": details.toggle_accounting,
        "collapse_cluster_servers": callbacks["toggle_cluster_servers"],
        "collapse_advanced": details.toggle_advanced,
        "btn_raw_job_details": details.raw_details,
        "btn_raw_accounting": details.raw_accounting,
        "btn_sacct": details.refresh_accounting,
        "btn_raw_server_status": cluster.raw_status,
        "accounting_box": details.accounting_box,
        "accounting_warning": details.accounting_warning,
        "cluster_servers_box": cluster.servers_box,
        "cluster_status_text": cluster.status_text,
        "advanced_box": details.advanced_box,
        "files_browser": files.browser,
        "files_model": files.model,
        "files_no_selection_panel": files.no_selection_panel,
        "files_job_header": files.job_header,
        "files_workdir_label": files.workdir_label,
        "open_main_files": files.open_main_files,
        "output_channel_notebook": outputs.channel_notebook,
        "output_no_channels_label": outputs.no_channels_label,
        "output_channels": outputs.channels,
        "output_channel_paths": outputs.channel_paths,
        "output_channel_status": outputs.channel_status,
        "outputs_no_selection_panel": outputs.no_selection_panel,
        "details_go_to_jobs": details.go_to_jobs,
        "files_go_to_jobs": files.go_to_jobs,
        "outputs_go_to_jobs": outputs.go_to_jobs,
        "outputs_refresh": outputs.refresh,
        "outputs_follow": outputs.follow,
        "outputs_pause": outputs.pause,
        "output_search": outputs.search_field,
        "output_find_next": outputs.find_next,
        "output_jump_latest": outputs.jump_latest,
        "output_open_window": outputs.open_window,
        "output_show_files": outputs.show_files,
        "filter_field": jobs.filter_field,
        "cb_auto_refresh": jobs.auto_refresh,
        "hide_finished": jobs.hide_finished,
        "btn_cancel": jobs.cancel,
        "delete_selected_details": callbacks["delete_details"],
        "jobs_refresh_label": jobs.refresh_label,
        "jobs_sort": callbacks["sort_jobs"],
        "cluster_servers_text": cluster.servers_text,
        "cluster_servers_table": cluster.servers_table,
        "btn_refresh_lssrv": cluster.refresh,
        "open_output_window": callbacks["open_output_window"],
        "go_to_jobs": callbacks["go_to_jobs"],
        "show_details_content": callbacks["show_details_content"],
    }
