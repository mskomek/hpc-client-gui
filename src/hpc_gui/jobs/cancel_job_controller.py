"""Identity-safe Slurm cancellation workflow and visible outcome reporting."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Thread
from typing import Any, Callable

from hpc_gui.core.i18n import t
from hpc_gui.services.job_identity import cancel_is_safe, make_identity
from hpc_gui.services.job_list_filter_sort import cancel_target_is_safe
from hpc_gui.services.job_submit_cancel import (
    build_cancel_confirmation,
    cancel_capability_available,
    reflect_cancel_result,
)


@dataclass
class CancelJobBindings:
    wx: Any
    state: dict[str, Any]
    model: Any
    kwargs: dict[str, Any]
    cancel: Callable | None
    final_state: Callable | None
    post: Callable
    refresh_jobs: Callable
    cancel_button: Any


class CancelJobController:
    """Guard cancellation by the selected scoped identity and report results."""

    def __init__(self, bindings: CancelJobBindings) -> None:
        self.bindings = bindings

    def cancel_job(self, _event=None) -> None:
        b, state = self.bindings, self.bindings.state
        wx = b.wx
        job_id = b.model.tracking.selected_job_id
        if not job_id or state["cancel_in_flight"]:
            return
        cancel_backend = b.cancel
        if not callable(cancel_backend):
            slurm_probe = b.kwargs.get("slurm_backend")
            if not cancel_capability_available(slurm_probe):
                state["cancel_capability"] = "unavailable"
                state["last_cancel_outcome"] = "UNAVAILABLE"
                state["last_cancel_message"] = "Cancel is unavailable for this provider."
                try:
                    b.cancel_button.Enable(False)
                except Exception:
                    pass
                return
        state["cancel_capability"] = "available"
        if not cancel_backend:
            return
        if not cancel_target_is_safe(
            state.get("selected_job", ""), list(state.get("raw_items", [])), job_id
        ):
            b.cancel_button.Enable(False)
            return
        identity_args = {
            "profile_id": str(b.kwargs.get("profile_id", "")),
            "cluster_id": str(b.kwargs.get("cluster_id", "")),
            "provider_id": str(b.kwargs.get("provider_id", "")),
            "session_generation": int(state.get("provider_generation", 0)),
        }
        selected_identity = make_identity(state.get("selected_job", ""), **identity_args)
        requested_identity = make_identity(job_id, **identity_args)
        if not cancel_is_safe(selected_identity, requested_identity):
            b.cancel_button.Enable(False)
            return
        context = b.model.selected_job_store.context
        try:
            expected_wording = build_cancel_confirmation(job_id, context.name or "")
        except Exception:
            expected_wording = ""
        name_part = f" ({context.name})" if context.name else ""
        try:
            message = t("jobs.cancel_confirm").format(job_id=job_id + name_part)
        except Exception:
            message = expected_wording or f"Cancel job {job_id}?"
        if expected_wording and expected_wording not in message and job_id not in message:
            message = expected_wording
        if wx.MessageBox(
            message, t("jobs.cancel"), wx.YES_NO | wx.ICON_WARNING
        ) != wx.YES:
            return
        state["cancel_in_flight"] = True
        b.cancel_button.Enable(False)

        def worker():
            try:
                output = cancel_backend(job_id)
                b.post(self._cancel_done, None, str(output or ""), job_id)
            except Exception as error:
                b.post(self._cancel_done, error, "", job_id)

        Thread(target=worker, daemon=True).start()

    def _cancel_done(self, error, output_text, job_id) -> None:
        b, state, wx = self.bindings, self.bindings.state, self.bindings.wx
        state["cancel_in_flight"] = False
        if state["closed"]:
            return
        final = ""
        try:
            if callable(b.final_state):
                final = str(b.final_state(job_id) or "")
        except Exception:
            pass
        result = reflect_cancel_result(
            error, output_text, job_id=job_id, final_state=final
        )
        state["last_cancel_outcome"] = result.outcome
        state["last_cancel_message"] = result.message
        state["last_cancel_is_error"] = result.is_error
        try:
            icon = wx.ICON_ERROR if result.is_error else wx.ICON_INFORMATION
            wx.MessageBox(result.message, t("jobs.cancel"), wx.OK | icon)
        except Exception:
            pass
        try:
            b.cancel_button.Enable(True)
        except Exception:
            pass
        if result.should_refresh:
            try:
                b.refresh_jobs()
            except Exception:
                pass
