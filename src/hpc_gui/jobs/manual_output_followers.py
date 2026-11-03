"""Manual output followers created from Files and output path actions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Callable
from uuid import uuid4

from hpc_gui.jobs.output_workspace import show_job_output
from hpc_gui.services.output_channel_resolver import TrackedOutput
from hpc_gui.services.output_follower import OutputFollower, OutputFollowerState


@dataclass
class ManualFollowerBindings:
    state: dict[str, Any]
    model: Any
    host: Any
    lifecycle: Any
    files_browser: Any
    remote_reader: Callable | None
    remote_statter: Callable | None
    channel_paths: dict[str, Any]
    channels: dict[str, Any]
    resolve_channels: Callable
    ensure_tabs: Callable
    refresh_single: Callable
    refresh_outputs: Callable
    select_page: Callable
    outputs_page: Any


class ManualOutputFollowers:
    """Maintain manually selected remote files as scoped output followers."""

    def __init__(self, bindings: ManualFollowerBindings) -> None:
        self.bindings = bindings

    def follow_file(self, remote_path, mode="new_tab", follower_id=None) -> None:
        b, state = self.bindings, self.bindings.state
        context = b.model.selected_job_store.context
        if not context.job_id:
            return
        path = str(remote_path)
        label = PurePosixPath(path).name or path
        if mode == "existing" and follower_id:
            self._replace_existing(follower_id, path, label, context)
            return
        tracking_id = f"follower-{uuid4().hex}"
        tracked = TrackedOutput(
            tracking_id=tracking_id, channel_id=None, label=label,
            path=path, origin="manual", job_id=context.job_id,
        )
        state.setdefault("tracked_outputs", []).append(tracked)
        follower = self._new_follower(tracking_id, path, label, context)
        if mode == "new_window":
            show_job_output(
                b.host, b.model, tracking_id, follower=follower,
                read_path=b.remote_reader, stat_path=b.remote_statter,
                lifecycle=b.lifecycle,
                on_closed=lambda: self.remove(tracking_id),
            )
        else:
            b.ensure_tabs(b.resolve_channels())
            b.refresh_single(tracking_id)
            b.select_page(b.outputs_page)

    def remove(self, tracking_id) -> None:
        b, state = self.bindings, self.bindings.state
        state["tracked_outputs"][:] = [
            item for item in state.get("tracked_outputs", ())
            if item.tracking_id != tracking_id
        ]
        state.get("followers", {}).pop(tracking_id, None)
        b.refresh_outputs(force=True)

    def _replace_existing(self, tracking_id, path, label, context) -> None:
        b, state = self.bindings, self.bindings.state
        tracked = state.get("tracked_outputs", [])
        previous = next(
            (item for item in tracked if item.tracking_id == tracking_id), None
        )
        if previous is None:
            return
        tracked[tracked.index(previous)] = TrackedOutput(
            tracking_id=tracking_id, channel_id=None, label=label,
            path=path, origin="manual", job_id=context.job_id,
        )
        follower = state.setdefault("followers", {}).get(tracking_id)
        if follower is None:
            follower = self._new_follower(tracking_id, path, label, context)
        else:
            follower.assign(
                channel_id=None, job_id=context.job_id, generation=context.generation,
                label=label, path=path, origin="manual", roles=("manual",),
            )
        path_control = b.channel_paths.get(tracking_id)
        if path_control:
            path_control.SetValue(path)
        text_control = b.channels.get(tracking_id)
        if text_control:
            text_control.SetValue("")
        b.refresh_outputs(force=True)
        b.select_page(b.outputs_page)

    def _new_follower(self, tracking_id, path, label, context):
        follower = OutputFollower(OutputFollowerState(
            tracking_id=tracking_id, channel_id=None, job_id=context.job_id,
            generation=context.generation, label=label, path=path,
            origin="manual", roles=("manual",),
        ))
        self.bindings.state.setdefault("followers", {})[tracking_id] = follower
        return follower
