"""Jobs table filtering, ordering, and wx row rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hpc_gui.jobs.job_rows import parse_job_row, prepare_job_list
from hpc_gui.config import storage


@dataclass
class JobListBindings:
    state: dict[str, Any]
    table: Any
    page_sizer: Any
    empty_label: Any
    cancel_button: Any
    hide_finished: Any
    filter_field: Any
    column_keys: tuple[str, ...]
    wx: Any


class JobListController:
    """Keep the scheduler snapshot separate from filtered visible rows."""

    def __init__(self, bindings: JobListBindings) -> None:
        self.bindings = bindings

    def render_items(self, items) -> None:
        self.bindings.state["raw_items"] = list(items or [])
        self.apply_filter()

    def on_column_click(self, event) -> None:
        state = self.bindings.state
        column = event.GetColumn()
        if 0 <= column < len(self.bindings.column_keys):
            key = self.bindings.column_keys[column]
            if state.get("sort_key") == key:
                state["sort_reverse"] = not bool(state.get("sort_reverse", False))
            else:
                state["sort_key"] = key
                state["sort_reverse"] = False
            self.apply_filter()
        try:
            event.Skip()
        except Exception:
            pass

    def on_filter_changed(self, _event=None) -> None:
        self.bindings.state["filter_query"] = self.bindings.filter_field.GetValue().strip()
        self.apply_filter()

    def toggle_hide_finished(self, _event=None) -> None:
        storage.set_hide_finished_jobs_enabled(self.bindings.hide_finished.GetValue())
        self.apply_filter()

    def apply_filter(self) -> None:
        bindings = self.bindings
        state = bindings.state
        filtered = prepare_job_list(
            list(state["raw_items"]), query=state["filter_query"],
            hide_finished=bindings.hide_finished.GetValue(),
            sort_key=state.get("sort_key", ""),
            reverse=bool(state.get("sort_reverse", False)),
        )
        paired = [(parse_job_row(item), item) for item in filtered]
        state["items"] = list(filtered)
        self.refresh_rows(paired)

    def refresh_rows(self, filtered) -> None:
        bindings = self.bindings
        state, table, wx = bindings.state, bindings.table, bindings.wx
        selected_ids = set(state.get("bulk_selected_job_ids", set()))
        selected_ids.update(
            table.GetItemText(index, 0)
            for index in range(table.GetItemCount())
            if table.GetItemState(index, wx.LIST_STATE_SELECTED)
        )
        state["bulk_selected_job_ids"] = selected_ids
        state["rendering_jobs"] = True
        table.DeleteAllItems()
        selected_still_visible = False
        bindings.empty_label.Show(not filtered)
        for row, _item in filtered:
            index = table.InsertItem(table.GetItemCount(), row["job_id"])
            for column, key in enumerate(("name", "state", "partition", "elapsed", "nodes", "cpus", "reason"), start=1):
                table.SetItem(index, column, row[key])
            if row["job_id"] in selected_ids or row["job_id"] == state["selected_job"]:
                selected_still_visible = True
                table.Select(index)
                table.SetItemState(index, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
        state["rendering_jobs"] = False
        if not selected_still_visible and state["selected_job"]:
            bindings.cancel_button.Enable(False)
        if not filtered:
            bindings.cancel_button.Enable(False)
        bindings.page_sizer.Layout()
