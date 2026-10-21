"""Language-change rendering for the Jobs workspace views."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from hpc_gui.core.i18n import t


@dataclass
class JobsLocalizationBindings:
    host: Any
    state: dict[str, Any]
    jobs: Any
    notebook: Any
    filter_label: Any
    filter_field: Any
    refresh_button: Any
    auto_refresh: Any
    hide_finished: Any
    cancel_button: Any
    jobs_empty_label: Any
    no_selection_label: Any
    no_selection_hint: Any
    go_to_jobs: Any
    files_no_selection_label: Any
    files_no_selection_hint: Any
    files_go_to_jobs: Any
    files_open_main_button: Any
    outputs_no_selection_label: Any
    outputs_no_selection_hint: Any
    outputs_go_to_jobs: Any
    detail_keys: tuple
    detail_labels: dict[str, Any]
    details_warning: Any
    raw_details_button: Any
    accounting_box: Any
    accounting_button: Any
    accounting_table: Any
    accounting_column_keys: tuple
    accounting_column_labels: dict[str, str]
    accounting_warning: Any
    raw_accounting_button: Any
    cluster_heading: Any
    cluster_status_text: Any
    cluster_servers_box: Any
    cluster_refresh_button: Any
    cluster_raw_button: Any
    cluster_servers_table: Any
    advanced_box: Any
    update_summary_header: Callable
    update_files_header: Callable
    files_header: Any
    files_no_selection_panel: Any
    outputs_refresh_button: Any
    outputs_follow: Any
    outputs_pause_button: Any
    output_channels: dict[str, Any]
    output_channel_notebook: Any
    output_channel_path_labels: dict[str, Any]
    output_channel_pause_buttons: dict[str, Any]
    output_channel_paused: dict[str, bool]
    output_channel_status: dict[str, Any]
    output_channel_status_keys: dict[str, str]
    output_no_channels_label: Any
    translate: Callable = t


class JobsLocalizationController:
    """Refresh visible labels while retaining the current workspace state."""

    def __init__(self, bindings: JobsLocalizationBindings) -> None:
        self.bindings = bindings

    def refresh_labels(self, _language=None) -> None:
        b, t = self.bindings, self.bindings.translate
        b.host.set_host_title(t("jobs.title"))
        b.filter_label.SetLabel(f"{t('common.filter')}:")
        try:
            b.filter_field.SetHint(t("jobs.filter_hint"))
        except Exception:
            pass
        b.refresh_button.SetLabel(t("jobs.refresh"))
        b.auto_refresh.SetLabel(t("jobs.auto_refresh"))
        b.hide_finished.SetLabel(t("jobs.hide_finished"))
        b.cancel_button.SetLabel(t("jobs.cancel"))
        b.jobs_empty_label.SetLabel(t("jobs_outputs.no_active_jobs"))
        column_keys = (
            "job_id", "name", "state", "partition", "elapsed", "nodes", "cpus", "reason"
        )
        labels = {
            "job_id": "jobs.job_id", "name": "jobs.name", "state": "jobs.state",
            "partition": "jobs.partition", "elapsed": "jobs.elapsed",
            "nodes": "jobs.nodes", "cpus": "jobs.cpus", "reason": "jobs.node_or_reason",
        }
        for index, key in enumerate(column_keys):
            info = b.jobs.GetColumn(index)
            info.Text = t(labels[key])
            b.jobs.SetColumn(index, info)
        for index, key in enumerate((
            "jobs.title", "jobs.cluster", "jobs.details",
            "jobs_outputs.files_title", "jobs_outputs.outputs_title",
        )):
            try:
                b.notebook.SetPageText(index, t(key))
            except Exception:
                pass
        b.no_selection_label.SetLabel(t("jobs.no_job_selected"))
        b.no_selection_hint.SetLabel(t("jobs.no_job_selected_hint"))
        b.go_to_jobs.SetLabel(t("jobs.go_to_jobs"))
        b.files_no_selection_label.SetLabel(t("jobs_outputs.no_selected_job"))
        b.files_no_selection_hint.SetLabel(t("jobs_outputs.no_selected_job_files_hint"))
        b.files_go_to_jobs.SetLabel(t("jobs.go_to_jobs"))
        if b.files_open_main_button is not None:
            b.files_open_main_button.SetLabel(t("jobs_outputs.open_main_files"))
        b.outputs_no_selection_label.SetLabel(t("jobs_outputs.no_selected_job"))
        b.outputs_no_selection_hint.SetLabel(t("jobs_outputs.no_selected_job_outputs_hint"))
        b.outputs_go_to_jobs.SetLabel(t("jobs.go_to_jobs"))
        b.update_summary_header()
        for field, label_key in b.detail_keys:
            if field in b.detail_labels:
                b.detail_labels[field].SetLabel(t(label_key))
        for field in ("nodes", "cpus"):
            if field in b.detail_labels:
                b.detail_labels[field].SetLabel(t(f"jobs.{field}"))
        if "resources" in b.detail_labels:
            b.detail_labels["resources"].SetLabel(t("jobs.resources"))
        if b.details_warning.IsShown():
            b.details_warning.SetLabel(t("jobs_outputs.parse_error_details"))
        if b.accounting_warning.IsShown():
            b.accounting_warning.SetLabel(t("jobs_outputs.parse_error_accounting"))
        b.raw_details_button.SetLabel(t("raw_viewer.raw_job_details"))
        prefix = "▸" if b.state["accounting_collapsed"] else "▾"
        b.accounting_box.SetLabel(f"{prefix} {t('jobs_outputs.accounting_details')}")
        b.accounting_button.SetLabel(t("jobs_outputs.refresh_sacct"))
        for index, key in enumerate(b.accounting_column_keys):
            info = b.accounting_table.GetColumn(index)
            info.Text = t(b.accounting_column_labels[key])
            b.accounting_table.SetColumn(index, info)
        b.raw_accounting_button.SetLabel(t("raw_viewer.raw_accounting"))
        b.cluster_heading.SetLabel(t("jobs_outputs.cluster_status"))
        b.cluster_status_text.SetLabel(t(b.state.get(
            "cluster_status_key", "jobs_outputs.no_cluster_connection"
        )))
        b.cluster_servers_box.SetLabel(t("jobs.cluster_servers"))
        b.cluster_refresh_button.SetLabel(t("jobs.refresh"))
        b.cluster_raw_button.SetLabel(t("raw_viewer.raw_server_status"))
        for index, key in enumerate(("partition", "free_cpus", "total_cpus", "memory_per_core")):
            info = b.cluster_servers_table.GetColumn(index)
            info.Text = t(f"jobs.{key}")
            b.cluster_servers_table.SetColumn(index, info)
        prefix = "▸" if b.state["advanced_collapsed"] else "▾"
        b.advanced_box.SetLabel(f"{prefix} {t('jobs.advanced')}")
        b.update_files_header()
        b.files_header.Layout()
        b.files_no_selection_panel.Layout()
        b.outputs_refresh_button.SetLabel(t("jobs_outputs.refresh_all"))
        b.outputs_follow.SetLabel(t("jobs_outputs.auto_scroll_all"))
        key = "jobs_outputs.resume_all" if b.state["outputs_paused"] else "jobs_outputs.pause_all"
        b.outputs_pause_button.SetLabel(t(key))
        self._refresh_output_channel_labels()

    def _refresh_output_channel_labels(self) -> None:
        b, t = self.bindings, self.bindings.translate
        channels = b.state.get("resolved_channels", ())
        for channel_id, text_ctrl in b.output_channels.items():
            page = text_ctrl.GetParent()
            try:
                index = b.output_channel_notebook.GetPageIndex(page)
                label = next((ch.label for ch in channels if ch.id == channel_id), channel_id)
                b.output_channel_notebook.SetPageText(index, label)
            except Exception:
                pass
            if channel_id in b.output_channel_path_labels:
                b.output_channel_path_labels[channel_id].SetLabel(f"{t('jobs_outputs.path')}:")
            if channel_id in b.output_channel_pause_buttons:
                label_key = (
                    "jobs.resume_output"
                    if b.output_channel_paused.get(channel_id, False)
                    else "jobs.pause_output"
                )
                b.output_channel_pause_buttons[channel_id].SetLabel(t(label_key))
            if channel_id in b.output_channel_status:
                status_key = b.output_channel_status_keys.get(
                    channel_id, "jobs_outputs.status_following"
                )
                b.output_channel_status[channel_id].SetLabel(
                    f"{t('jobs_outputs.status')}: {t(status_key)}"
                )
        try:
            b.output_no_channels_label.SetLabel(t("jobs_outputs.no_channels"))
        except Exception:
            pass
