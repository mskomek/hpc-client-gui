"""Asynchronous scheduler refresh and stale-snapshot preservation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Thread
from typing import Any, Callable

from hpc_gui.core.i18n import t
from hpc_gui.jobs.job_rows import parse_job_row
from hpc_gui.services.slurm_models import is_active_state


@dataclass
class JobsRefreshBindings:
    list_jobs: Callable | None
    state: dict[str, Any]
    state_lock: Any
    model: Any
    post: Callable
    generation: Callable | None
    refresh_label: Any
    render_items: Callable
    cancel_button: Any
    cancel: Callable | None
    final_state: Callable | None
    translate: Callable = t


class JobsRefreshController:
    """Fetch, merge, and apply scheduler snapshots without losing good data."""

    def __init__(self, bindings: JobsRefreshBindings) -> None:
        self.bindings = bindings

    @staticmethod
    def _has_key(key: str, translate: Callable) -> bool:
        try:
            return bool(translate(key) != f"[{key}]")
        except Exception:
            return False

    def refresh_jobs(self, _event=None) -> None:
        b = self.bindings
        state = b.state
        if not b.list_jobs or state["minimized"]:
            return
        request_generation = b.generation() if b.generation else None
        if request_generation is not None:
            b.model.set_monitor_generation(request_generation)
        with b.state_lock:
            if state["closed"]:
                return
            if state["in_flight"]:
                state["refresh_pending"] = True
                return
            state["in_flight"] = True
            state["jobs_refresh_seq"] += 1
            request_seq = state["jobs_refresh_seq"]
            machine = state["jobs_refresh"]
            machine.begin()
            state["jobs_refresh_status"] = "refreshing"
            try:
                b.refresh_label.SetLabel(b.translate("jobs.refreshing"))
            except Exception:
                pass

        def fetch():
            try:
                result = b.list_jobs()
                b.post(done, result, None, request_generation, request_seq)
            except Exception as error:
                b.post(done, (), error, request_generation, request_seq)

        def done(result, error, req_gen=None, req_seq=None):
            with b.state_lock:
                state["in_flight"] = False
                refresh_pending = state.pop("refresh_pending", False)
            if req_seq is not None and req_seq != state["jobs_refresh_seq"]:
                if refresh_pending and not state["closed"]:
                    b.post(self.refresh_jobs)
                return
            if not state["closed"] and (b.generation is None or req_gen == b.generation()):
                machine = state["jobs_refresh"]
                if error:
                    self._apply_failure(machine, error, req_seq)
                else:
                    self._apply_success(machine, result, req_seq, req_gen)
            if refresh_pending and not state["closed"]:
                b.post(self.refresh_jobs)

        Thread(target=fetch, daemon=True).start()

    def _apply_failure(self, machine, error, request_seq) -> None:
        b, state = self.bindings, self.bindings.state
        applied = machine.complete_failure(
            request_seq if request_seq is not None else machine.sequence, error
        )
        if not applied:
            return
        state["jobs_refresh_applied_seq"] = machine.applied_sequence
        state["jobs_refresh_status"] = "failure"
        state["jobs_refresh_error"] = machine.last_error
        state["jobs_refresh_stale"] = machine.stale
        try:
            key = "jobs.refresh_failed_stale" if machine.stale else "jobs.refresh_failed"
            fallback = "Refresh failed (stale)" if machine.stale else "Refresh failed"
            label = b.translate(key) if self._has_key(key, b.translate) else fallback
            b.refresh_label.SetLabel(f"{label}: {machine.last_error}")
        except Exception:
            pass

    def _apply_success(self, machine, result, request_seq, request_generation) -> None:
        b, state = self.bindings, self.bindings.state
        if isinstance(result, dict):
            items = tuple(result.get("jobs") or ())
            state["history_stale"] = bool(result.get("history_stale", False))
            state["history_error"] = str(result.get("history_error", ""))
        else:
            items = tuple(result or ())
        applied = machine.complete_success(
            request_seq if request_seq is not None else machine.sequence,
            list(items), timestamp=datetime.now(timezone.utc).isoformat(),
        )
        if not applied:
            return
        state["jobs_refresh_applied_seq"] = machine.applied_sequence
        state["jobs_refresh_status"] = "success"
        state["jobs_refresh_timestamp"] = machine.last_success_ts
        state["jobs_refresh_error"] = ""
        state["jobs_refresh_stale"] = False
        try:
            key = "jobs.refresh_updated"
            label = (
                f"{b.translate(key)}: {machine.last_success_ts}"
                if self._has_key(key, b.translate)
                else f"Updated: {machine.last_success_ts}"
            )
            b.refresh_label.SetLabel(label)
        except Exception:
            pass
        b.render_items(items)
        self._apply_selected_metadata(items)
        b.model.poll_active_jobs(items, b.final_state, generation=request_generation)

    def _apply_selected_metadata(self, items) -> None:
        b, state = self.bindings, self.bindings.state
        selected_id = state["selected_job"]
        for item in items:
            if not isinstance(item, dict):
                continue
            job_id = str(item.get("id", item.get("job_id", ""))).strip()
            b.model._job_states.setdefault(job_id, str(item.get("state", "")).strip().upper())
            if job_id != selected_id:
                continue
            row = parse_job_row(item)
            b.model.selected_job_store.update(
                state=row["state"], name=row["name"], partition=row["partition"],
                elapsed=row["elapsed"], nodes=row["nodes"], cpus=row["cpus"],
                reason=row["reason"], workdir=str(item.get("workdir", "")),
                workdir_source=str(item.get("workdir_source", item.get("source", ""))),
                stdout_path=str(item.get("stdout_path", "")),
                stderr_path=str(item.get("stderr_path", "")),
            )
            b.cancel_button.Enable(is_active_state(row["state"]) and bool(b.cancel))
