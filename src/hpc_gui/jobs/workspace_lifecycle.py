"""Jobs workspace shutdown, profile-switch, and restore lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any, Callable

from hpc_gui.core.i18n import t, unsubscribe_language_change
from hpc_gui.jobs.job_rows import parse_job_row


@dataclass
class WorkspaceLifecycleActions:
    ensure_output_tabs: Callable
    update_outputs_visibility: Callable
    set_output_channel_status: Callable
    clear_detail_values: Callable
    show_details_content: Callable
    reset_files_browser: Callable
    show_files_selected_state: Callable
    update_files_header: Callable
    refresh_provider_status: Callable
    refresh_jobs: Callable
    show_job_details: Callable
    refresh_job_metadata: Callable
    navigate_files_to_workdir: Callable
    refresh_outputs_tab: Callable
    show_parsed_details: Callable
    show_details_content: Callable
    update_summary_header: Callable
    refresh_accounting: Callable


@dataclass
class WorkspaceLifecycleBindings:
    wx: Any
    host: Any
    state: dict[str, Any]
    state_lock: RLock
    timer: Any
    notebook: Any
    outputs_page: Any
    auto_refresh: Any
    model: Any
    embedded: bool
    refresh_labels: Callable
    filter_field: Any
    search_field: Any
    cancel_button: Any
    outputs_pause_button: Any
    outputs_no_selection_panel: Any
    files_browser: Any
    output_channel_pause_buttons: dict[str, Any]
    output_channel_paused: dict[str, bool]
    output_channel_status: dict[str, Any]
    remote_callbacks: dict[str, Any]
    kwargs: dict[str, Any]
    actions: WorkspaceLifecycleActions


class JobsWorkspaceLifecycle:
    """Own teardown and session-generation invalidation for one workspace."""

    def __init__(self, bindings: WorkspaceLifecycleBindings) -> None:
        self.bindings = bindings

    def _close_files_browser(self) -> None:
        bindings = self.bindings
        if bindings.state["files_browser_closed"]:
            return
        bindings.state["files_browser_closed"] = True
        close_browser = getattr(bindings.files_browser, "_wx_host_close", None)
        if callable(close_browser):
            close_browser()

    def close(self, _event=None) -> None:
        bindings = self.bindings
        with bindings.state_lock:
            if bindings.state["closed"]:
                return
            bindings.state["closed"] = True
            bindings.state["outputs_pending_generations"].clear()
        self._close_files_browser()
        bindings.timer.Stop()
        unsubscribe_language_change(bindings.refresh_labels)
        # Embedded pages belong to the parent notebook. Standalone windows own
        # their destruction; destroying an embedded page leaves stale wx refs.
        if not bindings.embedded:
            bindings.host.Hide()
            bindings.host.Destroy()

    def on_destroy(self, event) -> None:
        bindings = self.bindings
        if event.GetEventObject() is not bindings.host:
            event.Skip()
            return
        with bindings.state_lock:
            bindings.state["closed"] = True
            bindings.state["outputs_pending_generations"].clear()
        self._close_files_browser()
        bindings.timer.Stop()
        for follower in bindings.state.get("followers", {}).values():
            follower.close()
        unsubscribe_language_change(bindings.refresh_labels)
        event.Skip()

    def set_session(self, session) -> None:
        bindings = self.bindings
        state, model, actions = bindings.state, bindings.model, bindings.actions
        profile = (session or {}).get("profile") or {}
        new_cluster_id = str(profile.get("cluster_id", profile.get("id", profile.get("profile_id", ""))))
        current_cluster_id = model.selected_job_store.context.cluster_id or str(bindings.kwargs.get("cluster_id", ""))
        previous_session_id = str((state.get("session") or {}).get("id", ""))
        next_session_id = str((session or {}).get("id", ""))
        same_session = bool(previous_session_id and next_session_id and previous_session_id == next_session_id)
        same_cluster = bool(current_cluster_id and new_cluster_id and current_cluster_id == new_cluster_id)
        keep_selection = bool(state["selected_job"] and (same_cluster or same_session))
        state["session"] = session
        state["provider_generation"] += 1
        if not keep_selection:
            state["selected_job"] = ""
        state["selected_generation"] += 1
        state["outputs_generation"] += 1
        for key in ("outputs_request_id", "sacct_request_id", "details_request_id", "status_request_id"):
            state[key] += 1
        state["raw_details_result"] = None
        state["raw_accounting_result"] = None
        state["raw_status_result"] = None
        for key in ("details_parse_error", "accounting_parse_error", "status_parse_error"):
            state[key] = ""
        state["outputs_paused"] = state["user_paused"] = state["_timer_paused"] = False
        state["outputs_pending_generations"].clear()
        state["outputs_requests"] = len(state["outputs_active_generations"])
        state["outputs_in_flight"] = bool(state["outputs_active_generations"])
        bindings.filter_field.SetValue("")
        bindings.search_field.SetValue("")
        model.tracking.set_session(session)
        bindings.cancel_button.Enable(False)
        for follower in state.get("followers", {}).values():
            follower.close()
        state["followers"].clear()
        state["tracked_outputs"].clear()
        for follower in state.get("detached_followers", ()):
            follower.close()
        state["detached_followers"].clear()
        for channel_id, button in bindings.output_channel_pause_buttons.items():
            bindings.output_channel_paused[channel_id] = False
            button.SetLabel(t("jobs.pause_output"))
        if not keep_selection:
            model.selected_job_store.clear()
        actions.ensure_output_tabs([])
        if not keep_selection:
            state["selected_job"] = ""
            model.tracking.select_job("")
            model.selected_job_store.clear()
        actions.update_outputs_visibility()
        bindings.outputs_no_selection_panel.Show(not bool(state.get("selected_job")))
        bindings.outputs_pause_button.SetLabel(t("jobs_outputs.pause_all"))
        for channel_id in bindings.output_channel_status:
            actions.set_output_channel_status(channel_id, "jobs_outputs.status_disconnected")
        if not keep_selection:
            actions.clear_detail_values()
            actions.show_details_content(False)
            actions.reset_files_browser()
            actions.show_files_selected_state(False)
        actions.update_files_header()
        set_navigation_store = getattr(bindings.files_browser, "_wx_remote_set_navigation_store", None)
        if callable(set_navigation_store):
            set_navigation_store((bindings.remote_callbacks or {}).get("navigation_store"))
        refresh_filters = getattr(bindings.files_browser, "_wx_remote_set_provider_filters", None)
        if callable(refresh_filters):
            try:
                remote = bindings.remote_callbacks or {}
                refresh_filters(
                    remote.get("provider_filters") or bindings.kwargs.get("provider_filters"),
                    remote.get("plugin_filters") or bindings.kwargs.get("plugin_filters"),
                )
            except Exception:
                pass
        actions.refresh_provider_status()
        actions.refresh_jobs()
        if keep_selection:
            actions.show_job_details()
            actions.refresh_job_metadata()
            actions.navigate_files_to_workdir()
            actions.refresh_outputs_tab(force=True)

    def iconized(self, event) -> None:
        bindings = self.bindings
        bindings.state["minimized"] = bool(event.IsIconized())
        if not bindings.state["minimized"]:
            bindings.actions.refresh_jobs()
        event.Skip()

    def on_page_changed(self, event) -> None:
        bindings = self.bindings
        actions, model, state = bindings.actions, bindings.model, bindings.state
        try:
            page_index = event.GetSelection()
            context = model.selected_job_store.context
            job_id = state.get("selected_job") or context.job_id
            if not job_id:
                event.Skip()
                return
            if not state.get("selected_job"):
                state["selected_job"] = job_id
                model.tracking.select_job(job_id)
            current_item = next((
                item for item in state.get("raw_items", ())
                if parse_job_row(item)["job_id"] == job_id
            ), {})
            item = dict(current_item) if isinstance(current_item, dict) else {}
            row = parse_job_row(item) if item else {"job_id": job_id}
            context_fields = (
                "name", "state", "partition", "elapsed", "nodes", "cpus", "reason",
                "workdir", "stdout_path", "stderr_path", "script_path", "nodelist",
                "exit_code", "failure_reason",
            )
            updates = {}
            for key in context_fields:
                value = getattr(context, key, "") or item.get(key, "")
                if value:
                    updates[key] = value
                    item[key] = value
                    if key in row:
                        row[key] = value
            updates["job_id"] = job_id
            model.selected_job_store.update(**updates)
            actions.show_parsed_details(row, item)
            actions.show_details_content(True)
            actions.update_summary_header()
            has_path_metadata = bool(context.workdir or context.stdout_path or context.stderr_path)
            if page_index == 2:
                if not has_path_metadata:
                    actions.show_job_details()
                    actions.refresh_job_metadata()
                actions.refresh_accounting()
            elif page_index == 3:
                actions.navigate_files_to_workdir()
                if not has_path_metadata:
                    actions.show_job_details()
                    actions.refresh_job_metadata()
            elif page_index == 4:
                if not has_path_metadata:
                    actions.show_job_details()
                    actions.refresh_job_metadata()
                actions.refresh_outputs_tab(force=True)
        except Exception:
            pass
        event.Skip()

    def tick(self, event) -> None:
        bindings = self.bindings
        actions, state = bindings.actions, bindings.state
        if bindings.auto_refresh.GetValue():
            actions.refresh_jobs(event)
        try:
            if bindings.notebook.GetCurrentPage() is bindings.outputs_page:
                context = bindings.model.selected_job_store.context
                terminal_states = {
                    "COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY"
                }
                terminal = context.state.upper() in terminal_states if context.state else False
                if terminal:
                    grace = state.get("_terminal_grace", 0)
                    if grace < 3:
                        state["_terminal_grace"] = grace + 1
                        actions.refresh_outputs_tab(event)
                    elif grace == 3:
                        state["_terminal_grace"] = grace + 1
                        actions.refresh_outputs_tab(event, force=True)
                else:
                    state["_terminal_grace"] = 0
                    actions.refresh_outputs_tab(event)
        except Exception:
            pass
