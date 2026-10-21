"""Search, detached viewing, and Files handoff for output channels."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Callable
from uuid import uuid4

from hpc_gui.core.i18n import t
from hpc_gui.jobs.output_workspace import show_job_output
from hpc_gui.services.output_follower import OutputFollower, OutputFollowerState


@dataclass
class OutputPanelInteractionBindings:
    wx: Any
    state: dict[str, Any]
    model: Any
    search_field: Any
    channel_notebook: Any
    output_channels: dict[str, Any]
    output_channel_paths: dict[str, Any]
    host: Any
    lifecycle: Any
    read_output: Callable | None
    remote_reader: Callable | None
    remote_statter: Callable | None
    files_workdir_label: Any
    files_browser: Any
    show_files_selected_state: Callable
    files_page: Any
    select_inner_page: Callable


class OutputPanelInteractions:
    """Provide per-channel search and actions without owning output fetching."""

    def __init__(self, bindings: OutputPanelInteractionBindings) -> None:
        self.bindings = bindings

    def active_channel_text(self):
        b = self.bindings
        selected = b.channel_notebook.GetSelection()
        if 0 <= selected < b.channel_notebook.GetPageCount():
            page = b.channel_notebook.GetPage(selected)
            for text_control in b.output_channels.values():
                if text_control.GetParent() == page:
                    return text_control
        for index in range(b.channel_notebook.GetPageCount()):
            page = b.channel_notebook.GetPage(index)
            for text_control in b.output_channels.values():
                if text_control.GetParent() == page:
                    b.channel_notebook.SetSelection(index)
                    return text_control
        return None

    def search(self, _event=None) -> None:
        b = self.bindings
        query = b.search_field.GetValue().strip()
        text_control = self.active_channel_text()
        if not query or not text_control:
            return
        position = text_control.GetValue().find(query)
        if position >= 0:
            text_control.SetStyle(
                position, position + len(query), b.wx.TextAttr(b.wx.RED, b.wx.YELLOW)
            )

    def find_next(self, _event=None) -> None:
        b = self.bindings
        query = b.search_field.GetValue().strip()
        text_control = self.active_channel_text()
        if not query or not text_control:
            return
        text = text_control.GetValue()
        position = text_control.GetInsertionPoint() + 1
        found = text.find(query, position)
        if found < 0:
            found = text.find(query)
        if found >= 0:
            text_control.SetInsertionPoint(found)
            text_control.SetSelection(found, found + len(query))

    def jump_latest(self, _event=None) -> None:
        text_control = self.active_channel_text()
        if text_control:
            text_control.ShowPosition(text_control.GetLastPosition())

    def open_detached(self, _event=None) -> None:
        b, state = self.bindings, self.bindings.state
        job_id = state.get("selected_job")
        if not callable(b.read_output) or not job_id:
            return
        view = b.model.open_detached()

        def read_stdout():
            result = b.read_output(job_id)
            if isinstance(result, dict):
                return result.get("stdout", "")
            if isinstance(result, (tuple, list)):
                return result[0] if result else ""
            return result

        show_job_output(
            b.host, b.model, view.id, read_output=read_stdout, lifecycle=b.lifecycle
        )

    def open_in_window(self, _event=None) -> None:
        b, state = self.bindings, self.bindings.state
        text_control = self.active_channel_text()
        job_id = state.get("selected_job")
        if not text_control or not job_id:
            return
        channel = next(
            (
                item for item in state.get("resolved_channels", ())
                if b.output_channels.get(item.id) == text_control
            ),
            None,
        )
        if channel is None:
            return
        follower = OutputFollower(OutputFollowerState(
            tracking_id=f"window-{uuid4().hex}", channel_id=channel.id,
            job_id=job_id, generation=b.model.selected_job_store.generation,
            label=channel.label, path=channel.path,
            origin="provider" if channel.definition else "legacy_slurm",
            roles=channel.roles,
        ))
        state.setdefault("detached_followers", []).append(follower)
        reader = b.remote_reader
        if not callable(reader) and callable(b.read_output) and set(channel.roles) & {"stdout", "stderr"}:
            reader = self._legacy_reader(job_id, channel.roles)
        if callable(reader):
            show_job_output(
                b.host, b.model, follower.state.tracking_id, follower=follower,
                read_path=reader, stat_path=b.remote_statter, lifecycle=b.lifecycle,
                on_closed=lambda item=follower: self._remove_detached(item),
            )

    def show_in_files(self, _event=None) -> None:
        b = self.bindings
        text_control = self.active_channel_text()
        if not text_control:
            return
        path = next(
            (
                b.output_channel_paths[channel_id].GetValue()
                for channel_id, control in b.output_channels.items()
                if control == text_control and channel_id in b.output_channel_paths
            ),
            "",
        )
        if not path:
            return
        parent = str(PurePosixPath(path).parent) or "/"
        b.files_workdir_label.SetLabel(f"{t('jobs_outputs.workdir')}: {parent}")
        try:
            tab_index = b.files_browser._wx_remote_notebook.GetSelection()
            tab = b.files_browser._wx_remote_tabs[tab_index]
            tab["highlight_path"] = path
            controls = b.files_browser._wx_remote_controls
            controls["navigate"](parent)
            controls["load"]()
        except Exception:
            pass
        b.show_files_selected_state(True)
        b.select_inner_page(b.files_page)

    def bind(self, controls) -> None:
        b = self.bindings
        controls["find_next"].Bind(b.wx.EVT_BUTTON, self.find_next)
        controls["jump_latest"].Bind(b.wx.EVT_BUTTON, self.jump_latest)
        controls["open_window"].Bind(b.wx.EVT_BUTTON, self.open_in_window)
        controls["show_files"].Bind(b.wx.EVT_BUTTON, self.show_in_files)
        try:
            b.search_field.Bind(b.wx.EVT_TEXT_ENTER, self.search)
        except Exception:
            pass

    def _legacy_reader(self, job_id, roles):
        callback = self.bindings.read_output

        def read(_path):
            result = callback(job_id)
            if isinstance(result, dict):
                key = "stdout" if "stdout" in roles else "stderr"
                return result.get(key, "")
            return result

        return read

    def _remove_detached(self, follower) -> None:
        followers = self.bindings.state.get("detached_followers", [])
        if follower in followers:
            followers.remove(follower)
