"""Presentation of normalized and archived Slurm job details."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hpc_gui.core.i18n import t


@dataclass
class JobDetailsViewBindings:
    state: dict[str, Any]
    model: Any
    no_selection_panel: Any
    content_panel: Any
    page_sizer: Any
    content_sizer: Any
    summary: Any
    values: dict[str, Any]
    warning: Any
    accounting_table: Any
    accounting_warning: Any


class JobDetailsPresenter:
    """Render partial records without erasing metadata missing from a response."""

    def __init__(self, bindings: JobDetailsViewBindings) -> None:
        self.bindings = bindings

    def show_content(self, show: bool) -> None:
        bindings = self.bindings
        if show:
            bindings.no_selection_panel.Hide()
            bindings.content_panel.Show()
        else:
            bindings.content_panel.Hide()
            bindings.no_selection_panel.Show()
        bindings.page_sizer.Layout()

    def clear_values(self) -> None:
        bindings = self.bindings
        for control in bindings.values.values():
            control.SetValue("—")
        bindings.summary.SetLabel(t("jobs.details_header"))
        bindings.state["details_parse_error"] = ""
        bindings.warning.Hide()
        bindings.accounting_table.DeleteAllItems()
        bindings.accounting_warning.Hide()

    def update_summary_header(self) -> None:
        context = self.bindings.model.selected_job_store.context
        parts = [value for value in (context.job_id, context.name) if value]
        summary = " · ".join(parts)
        self.bindings.summary.SetLabel(
            f"{t('jobs.details_header')} — {summary}" if summary else t("jobs.details_header")
        )

    def set_field(self, field_key: str, value: Any) -> None:
        control = self.bindings.values.get(field_key)
        if control is not None:
            control.SetValue(str(value or "—"))

    def show_parsed_details(self, row: dict[str, str], item: dict[str, Any]) -> None:
        bindings = self.bindings
        bindings.warning.Hide()
        for field_key in ("job_id", "name", "state", "partition", "elapsed", "nodes", "cpus"):
            self.set_field(field_key, row.get(field_key, ""))
        data = item if isinstance(item, dict) else {}
        workdir = str(data.get("workdir", "")).strip()
        stdout_path = str(data.get("stdout_path", "")).strip()
        stderr_path = str(data.get("stderr_path", "")).strip()
        script_path = str(data.get("script_path", "")).strip()
        nodelist = str(data.get("nodelist", "")).strip()
        exit_code = str(data.get("exit_code", "")).strip()
        reason = str(data.get("failure_reason", data.get("reason", row.get("reason", "")))).strip()
        for key, value in (
            ("workdir", workdir), ("stdout_path", stdout_path), ("stderr_path", stderr_path),
            ("script_path", script_path), ("nodelist", nodelist),
            ("exit_code", exit_code), ("reason", reason),
        ):
            self.set_field(key, value)
        nodes, cpus = row.get("nodes", ""), row.get("cpus", "")
        resources = t("jobs.resources_value").format(nodes=nodes or "?", cpus=cpus or "?") if nodes or cpus else "—"
        self.set_field("resources", resources)
        metadata = {
            "name": row.get("name", ""), "state": row.get("state", ""),
            "partition": row.get("partition", ""), "elapsed": row.get("elapsed", ""),
            "nodes": nodes, "cpus": cpus, "reason": reason, "workdir": workdir,
            "workdir_source": str(data.get("workdir_source", data.get("source", ""))).strip(),
            "stdout_path": stdout_path, "stderr_path": stderr_path, "script_path": script_path,
            "nodelist": nodelist, "exit_code": exit_code, "failure_reason": reason,
            "user": str(data.get("user", "")).strip(), "script_text": str(data.get("script_text", "")),
            "submit_directory": str(data.get("submit_directory", data.get("submit_dir", ""))),
        }
        updates = {key: value for key, value in metadata.items() if value}
        if updates:
            bindings.model.selected_job_store.update(**updates)
            context = bindings.model.selected_job_store.context
            bindings.model.set_output(context.stdout_path, context.stderr_path)