"""Primary job selection and independent bulk-selection behavior."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Callable

from hpc_gui.core.i18n import t
from hpc_gui.jobs.job_rows import parse_job_row
from hpc_gui.services.slurm_models import is_active_state


@dataclass
class JobSelectionBindings:
    wx: Any
    state: dict[str, Any]
    model: Any
    table: Any
    kwargs: dict[str, Any]
    cancel: Callable | None
    cancel_job: Callable
    refresh_jobs: Callable
    ensure_output_tabs: Callable
    update_outputs_visibility: Callable
    clear_detail_values: Callable
    show_details_content: Callable
    reset_files_browser: Callable
    show_files_selected_state: Callable
    update_files_header: Callable
    show_parsed_details: Callable
    update_summary_header: Callable
    detail_values: dict[str, Any]
    refresh_accounting: Callable
    show_job_details: Callable
    refresh_metadata: Callable
    navigate_files: Callable
    refresh_outputs: Callable
    cancel_button: Any
    translate: Callable = t


class JobSelectionController:
    """Coordinate one primary details job with a multi-row bulk selection."""

    def __init__(self, bindings: JobSelectionBindings) -> None:
        self.bindings = bindings

    def clear_job_selection(self) -> None:
        b, state = self.bindings, self.bindings.state
        state["selected_job"] = ""
        state["bulk_selected_job_ids"].clear()
        state["selected_generation"] += 1
        state["sacct_request_id"] += 1
        state["details_request_id"] += 1
        state["outputs_request_id"] += 1
        state["outputs_generation"] += 1
        state["raw_details_result"] = None
        state["raw_accounting_result"] = None
        state["details_parse_error"] = ""
        state["accounting_parse_error"] = ""
        b.model.tracking.select_job("")
        b.model.selected_job_store.clear()
        b.cancel_button.Enable(False)
        b.clear_detail_values()
        b.show_details_content(False)
        b.reset_files_browser()
        b.show_files_selected_state(False)
        b.ensure_output_tabs([])
        b.update_outputs_visibility()
        b.update_files_header(b.model.selected_job_store.context)

    def clear_job_row_selection(self) -> None:
        b = self.bindings
        for index in range(b.table.GetItemCount()):
            if b.table.GetItemState(index, b.wx.LIST_STATE_SELECTED):
                b.table.SetItemState(index, 0, b.wx.LIST_STATE_SELECTED)

    def on_jobs_left_down(self, event) -> None:
        b = self.bindings
        table, state, wx = b.table, b.state, b.wx
        index, _flags = table.HitTest(event.GetPosition())
        selected = bool(state.get("selected_job")) or any(
            table.GetItemState(row, wx.LIST_STATE_SELECTED)
            for row in range(table.GetItemCount())
        )
        if index >= 0 and table.GetItemState(index, wx.LIST_STATE_SELECTED):
            self.clear_job_selection()
            self.clear_job_row_selection()
            return
        if index < 0 and selected:
            self.clear_job_selection()
            self.clear_job_row_selection()
        event.Skip()

    def on_job_item_deselected(self, event) -> None:
        b = self.bindings
        if not b.state.get("rendering_jobs"):
            b.state["bulk_selected_job_ids"].discard(
                b.table.GetItemText(event.GetIndex(), 0)
            )
        event.Skip()

    def select_job(self, event) -> None:
        b, state = self.bindings, self.bindings.state
        index = event.GetIndex()
        if index < 0 or index >= len(state["items"]):
            return
        item = state["items"][index]
        row = parse_job_row(item)
        job_id = row["job_id"]
        if not job_id or job_id == state["selected_job"]:
            return
        state["selected_job"] = job_id
        state["bulk_selected_job_ids"].add(job_id)
        state["selected_generation"] += 1
        state["raw_details_result"] = None
        state["raw_accounting_result"] = None
        state["details_parse_error"] = ""
        state["accounting_parse_error"] = ""
        b.ensure_output_tabs([])
        b.model.tracking.select_job(job_id)
        b.cancel_button.Enable(True)
        b.model.selected_job_store.select(
            job_id=job_id,
            profile_id=str(b.kwargs.get("profile_id", "")),
            cluster_id=str(b.kwargs.get("cluster_id", "")),
            provider_id=str(b.kwargs.get("provider_id", "")),
            name=row["name"], state=row["state"], partition=row["partition"],
            elapsed=row["elapsed"], nodes=row["nodes"], cpus=row["cpus"],
            reason=row["reason"],
        )
        b.show_parsed_details(row, item if isinstance(item, dict) else {})
        if isinstance(item, dict):
            failure = b.model.explain_failure(SimpleNamespace(**item))
            if failure:
                reason = b.detail_values["reason"].GetValue()
                b.detail_values["reason"].SetValue(
                    f"{reason}\n{'; '.join(failure.as_lines())}".strip("—\n")
                )
        b.show_details_content(True)
        b.update_outputs_visibility()
        b.update_summary_header()
        b.refresh_accounting()
        b.show_job_details()
        b.refresh_metadata()
        b.navigate_files()
        b.refresh_outputs(force=True)
        # Selection updates details without changing the user's active tab.

    def on_jobs_right_click(self, event) -> None:
        b, state, wx = self.bindings, self.bindings.state, self.bindings.wx
        index = event.GetIndex()
        if index < 0 or index >= len(state.get("items", [])):
            return
        if not b.table.GetItemState(index, wx.LIST_STATE_SELECTED):
            self.clear_job_row_selection()
            b.table.SetItemState(index, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
            b.table.Select(index)
        self.select_job(event)
        row = parse_job_row(state["items"][index])
        menu = wx.Menu()
        cancel_item = menu.Append(wx.ID_ANY, b.translate("jobs.cancel"))
        cancel_item.Enable(
            bool(b.cancel) and is_active_state(row["state"])
            and not state["cancel_in_flight"]
        )
        menu.Bind(wx.EVT_MENU, b.cancel_job, id=cancel_item.GetId())
        delete_item = menu.Append(wx.ID_ANY, b.translate("jobs.delete_details"))
        delete_item.Enable(
            callable(b.kwargs.get("delete_job_details"))
            and b.table.GetSelectedItemCount() > 0
        )
        menu.Bind(wx.EVT_MENU, self.delete_selected_details, id=delete_item.GetId())
        b.table.PopupMenu(menu)
        menu.Destroy()

    def delete_selected_details(self, _event=None) -> None:
        b, state, wx = self.bindings, self.bindings.state, self.bindings.wx
        delete_records = b.kwargs.get("delete_job_details")
        selected_ids = list(state.get("bulk_selected_job_ids", set()))
        for index in range(b.table.GetItemCount()):
            if b.table.GetItemState(index, wx.LIST_STATE_SELECTED):
                selected_ids.append(b.table.GetItemText(index, 0))
        selected_ids = list(dict.fromkeys(job_id for job_id in selected_ids if job_id))
        if not selected_ids or not callable(delete_records):
            return
        message = b.translate("jobs.delete_details_confirm").format(
            count=len(selected_ids)
        )
        if wx.MessageBox(
            message, b.translate("jobs.delete_details"),
            wx.YES_NO | wx.ICON_WARNING,
        ) != wx.YES:
            return
        try:
            deleted = int(delete_records(selected_ids) or 0)
        except Exception as error:
            wx.MessageBox(
                str(error), b.translate("jobs.delete_details"),
                wx.OK | wx.ICON_ERROR,
            )
            return
        state["bulk_selected_job_ids"].difference_update(selected_ids)
        if state.get("selected_job") in selected_ids:
            self.clear_job_selection()
        wx.MessageBox(
            b.translate("jobs.delete_details_done").format(count=deleted),
            b.translate("jobs.delete_details"), wx.OK | wx.ICON_INFORMATION,
        )
        b.refresh_jobs()
