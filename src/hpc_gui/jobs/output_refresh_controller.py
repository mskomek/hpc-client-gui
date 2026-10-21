"""Asynchronous reads and rendering for per-job output channels."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from threading import Thread
from typing import Any, Callable

from hpc_gui.core.i18n import t
from hpc_gui.jobs.output_workspace import _output_at_bottom
from hpc_gui.services.output_follower import retain_last_lines


@dataclass
class OutputRefreshBindings:
    state: dict[str, Any]
    state_lock: Any
    model: Any
    begin_request: Callable
    finish_request: Callable
    output_owner: Callable
    set_status: Callable
    ensure_tabs: Callable
    resolve_channels: Callable
    update_visibility: Callable
    post: Callable
    read_output: Callable | None
    remote_reader: Callable | None
    remote_statter: Callable | None
    kwargs: dict[str, Any]
    channels: dict[str, Any]
    paused: dict[str, bool]
    follow: dict[str, bool]
    offsets: dict[str, int]
    waiting: dict[str, int]
    status: dict[str, Any]
    pause_buttons: dict[str, Any]
    auto_scroll: Any
    refresh_button: Any
    pause_all_button: Any


class OutputRefreshController:
    """Run output reads off-thread and reject responses for stale job epochs."""

    def __init__(self, bindings: OutputRefreshBindings) -> None:
        self.bindings = bindings

    def refresh_single_channel(self, channel_id: str) -> None:
        b = self.bindings
        context = b.model.selected_job_store.context
        if not context.job_id:
            return
        text_control = b.channels.get(channel_id)
        follower = b.state.get("followers", {}).get(channel_id)
        if text_control is None or follower is None:
            return
        owner = b.output_owner(context.job_id)
        request = b.begin_request(owner, True)
        if request is None:
            return
        request_id, output_generation = request

        def done(content, waiting, error, snapshot=False, missing=False):
            owner_current, pending_force = b.finish_request(owner)
            current = (
                owner_current
                and request_id == b.state["outputs_request_id"]
                and output_generation == b.state["outputs_generation"]
            )
            if current:
                if error is not None:
                    b.set_status(channel_id, "jobs_outputs.status_error")
                else:
                    if snapshot:
                        content = follower.replace_snapshot(content)
                    elif missing:
                        follower.state.waiting_state = min(follower.state.waiting_state + 1, 5)
                        content = follower.text
                    try:
                        text_control.SetValue(retain_last_lines(content))
                    except RuntimeError:
                        pass
                    b.set_status(
                        channel_id,
                        "jobs_outputs.status_waiting" if waiting else "jobs_outputs.status_following",
                    )
            if owner_current and pending_force is not None:
                self.refresh_outputs_tab(force=pending_force)

        def worker():
            try:
                follower.state.paused = b.paused.get(channel_id, False)
                if callable(b.remote_reader):
                    _chunk, content, waiting = follower.poll(b.remote_reader, b.remote_statter, force=True)
                elif callable(b.read_output) and set(follower.state.roles) & {"stdout", "stderr"}:
                    result = b.read_output(context.job_id)
                    content = (
                        result.get("stdout" if "stdout" in follower.state.roles else "stderr", "")
                        if isinstance(result, dict) else result
                    )
                    b.post(done, content, False, None, True)
                    return
                else:
                    raise RuntimeError(t("jobs_outputs.remote_reader_unavailable"))
                b.post(done, content, waiting, None)
            except Exception as error:
                b.post(done, "", False, error)

        try:
            Thread(target=worker, daemon=True).start()
        except Exception as error:
            done("", False, error)

    def refresh_outputs_tab(self, _event=None, *, force: bool = False) -> None:
        b = self.bindings
        state = b.state
        with b.state_lock:
            job_id = state["selected_job"]
            if state["closed"]:
                return
            if not job_id:
                b.ensure_tabs([])
                b.update_visibility()
                return
            if state.get("_timer_paused") and not force:
                return
        owner = b.output_owner(job_id)
        request = b.begin_request(owner, force)
        if request is None:
            return
        request_id, output_generation = request
        try:
            channels = b.resolve_channels()
            state["resolved_channels"] = channels
            b.ensure_tabs(channels)
        except Exception as error:
            owner_current, pending_force = b.finish_request(owner)
            if owner_current:
                for text_control in b.channels.values():
                    text_control.SetValue(str(error))
                    break
                for channel in state.get("resolved_channels", ()):
                    b.set_status(channel.id, "jobs_outputs.status_error")
            if owner_current and pending_force is not None:
                self.refresh_outputs_tab(force=pending_force)
            return

        def worker(generation=output_generation, resolved=channels, active_owner=owner, req_id=request_id):
            results = {}
            try:
                for channel in resolved:
                    follower = state.get("followers", {}).get(channel.id)
                    if follower is None:
                        continue
                    selected_context = b.model.selected_job_store.context
                    if (
                        callable(b.read_output)
                        and selected_context.job_id == active_owner[0]
                        and not selected_context.workdir
                        and not selected_context.stdout_path
                        and not selected_context.stderr_path
                        and channel.path
                        and not PurePosixPath(channel.path).is_absolute()
                        and set(channel.roles) & {"stdout", "stderr"}
                    ):
                        try:
                            legacy = b.read_output(active_owner[0])
                            if isinstance(legacy, dict):
                                values = [
                                    str(legacy.get(role, "") or "")
                                    for role in ("stdout", "stderr") if role in channel.roles
                                ]
                                content = "\n".join(dict.fromkeys(value for value in values if value))
                            elif isinstance(legacy, (tuple, list)):
                                content = "\n".join(str(value or "") for value in legacy if value)
                            else:
                                content = str(legacy or "")
                            results[channel.id] = (content, not bool(content), True, False, False)
                            continue
                        except (FileNotFoundError, OSError):
                            results[channel.id] = (None, True, False, True, False)
                            continue
                    if callable(b.remote_reader) and channel.path:
                        try:
                            _chunk, retained, waiting = follower.poll(b.remote_reader, b.remote_statter)
                        except PermissionError as error:
                            results[channel.id] = (str(error), False, False, False, True)
                            continue
                        results[channel.id] = (retained, waiting, False, False, False)
                        continue
                    if callable(b.read_output) and set(channel.roles) & {"stdout", "stderr"}:
                        try:
                            legacy = b.read_output(active_owner[0])
                            if isinstance(legacy, dict):
                                content = legacy.get("stdout" if "stdout" in channel.roles else "stderr", "")
                            elif isinstance(legacy, (tuple, list)):
                                index = 0 if "stdout" in channel.roles else 1
                                content = legacy[index] if legacy else ""
                            else:
                                content = legacy
                            results[channel.id] = (content, False, True, False, False)
                        except PermissionError as error:
                            results[channel.id] = (str(error), False, False, False, True)
                        except (FileNotFoundError, OSError):
                            results[channel.id] = (None, True, False, True, False)
                    else:
                        results[channel.id] = (follower.text, True, False, False, False)
            except Exception as error:
                b.post(done, results, error, req_id, generation, resolved, active_owner)
            else:
                b.post(done, results, None, req_id, generation, resolved, active_owner)

        def done(result, error, req_id, generation, resolved, active_owner):
            owner_current, pending_force = b.finish_request(active_owner)
            current = (
                owner_current and generation == state["outputs_generation"]
                and req_id == state["outputs_request_id"]
            )
            if current:
                if error:
                    self._show_cached_or_error(active_owner[0], resolved, error)
                else:
                    self._render_results(active_owner[0], resolved, result)
                    b.refresh_button.Enable(True)
            if owner_current and pending_force is not None:
                self.refresh_outputs_tab(force=pending_force)

        try:
            Thread(target=worker, daemon=True).start()
        except Exception as error:
            done({}, error, request_id, output_generation, channels, owner)

    def _show_cached_or_error(self, job_id, channels, error) -> None:
        b = self.bindings
        try:
            cached = b.kwargs.get("load_output_snapshots", lambda _job: {})(job_id)
        except Exception:
            cached = {}
        for channel in channels:
            snapshot = cached.get(channel.id) if isinstance(cached, dict) else None
            text_control = b.channels.get(channel.id)
            if snapshot and text_control is not None:
                text_control.SetValue(retain_last_lines(str(snapshot.get("text", ""))))
                status = b.status.get(channel.id)
                if status is not None:
                    status.SetLabel(t("jobs_outputs.status_cached").format(
                        captured_at=str(snapshot.get("captured_at", ""))
                    ))
            else:
                if text_control is not None:
                    text_control.SetValue(str(error))
                b.set_status(channel.id, "jobs_outputs.status_error")

    def _render_results(self, job_id, channels, results) -> None:
        b = self.bindings
        for channel in channels:
            text_control = b.channels.get(channel.id)
            if text_control is None:
                continue
            entry = results.get(channel.id, ("", False, False, False))
            if len(entry) == 5:
                content, waiting, snapshot, missing, channel_error = entry
            else:
                content, waiting, snapshot, missing = entry
                channel_error = False
            follower = b.state.get("followers", {}).get(channel.id)
            if follower is not None and snapshot:
                content = follower.replace_snapshot(content)
            elif follower is not None and missing:
                follower.state.waiting_state = min(follower.state.waiting_state + 1, 5)
                content = follower.text
            if channel_error:
                self._show_cached_or_error(job_id, [channel], content or "Permission denied")
                continue
            if not waiting and content and callable(b.kwargs.get("save_output_snapshot")):
                try:
                    b.kwargs["save_output_snapshot"](job_id, channel.id, channel.path, content)
                except Exception:
                    pass
            if b.paused.get(channel.id, False):
                b.set_status(channel.id, "jobs_outputs.status_paused")
                continue
            at_bottom = _output_at_bottom(text_control)
            text_control.SetValue(retain_last_lines(content))
            b.offsets[channel.id] = follower.state.offset if follower else 0
            b.waiting[channel.id] = follower.state.waiting_state if follower else 0
            terminal = str(b.model.selected_job_store.context.state).upper() in {
                "COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY",
            }
            status_key = "jobs_outputs.status_waiting" if waiting else (
                "jobs_outputs.status_completed" if terminal else "jobs_outputs.status_following"
            )
            b.set_status(channel.id, status_key)
            if (
                b.auto_scroll.GetValue() and b.follow.get(channel.id, True)
                and at_bottom and not b.state["minimized"]
            ):
                b.state["follow_calls"] += 1
                text_control.ShowPosition(text_control.GetLastPosition())

    def toggle_pause(self, _event=None) -> None:
        b = self.bindings
        b.state["outputs_paused"] = not b.state["outputs_paused"]
        b.state["user_paused"] = b.state["outputs_paused"]
        b.state["_timer_paused"] = b.state["outputs_paused"]
        b.pause_all_button.SetLabel(t(
            "jobs_outputs.resume_all" if b.state["outputs_paused"] else "jobs_outputs.pause_all"
        ))
        for channel_id, button in b.pause_buttons.items():
            b.paused[channel_id] = b.state["outputs_paused"]
            button.SetLabel(t("jobs.resume_output" if b.state["outputs_paused"] else "jobs.pause_output"))
            b.set_status(
                channel_id,
                "jobs_outputs.status_paused" if b.state["outputs_paused"]
                else "jobs_outputs.status_following",
            )