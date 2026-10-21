"""Dynamic output-channel tabs and provider channel resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from uuid import uuid4

from hpc_gui.core.i18n import current_language, t
from hpc_gui.services.output_channel_resolver import OutputResolver, ResolvedOutputChannel
from hpc_gui.services.output_follower import OutputFollower, OutputFollowerState


@dataclass
class OutputChannelBindings:
    wx: Any
    state: dict[str, Any]
    model: Any
    resolver: OutputResolver
    notebook: Any
    no_channels_label: Any
    channels: dict[str, Any]
    paths: dict[str, Any]
    paused: dict[str, bool]
    follow: dict[str, bool]
    pause_buttons: dict[str, Any]
    status: dict[str, Any]
    status_keys: dict[str, str]
    path_labels: dict[str, Any]
    offsets: dict[str, int]
    in_flight: dict[str, bool]
    waiting: dict[str, int]
    refresh_single: Callable[[str], None] | None = None


class OutputChannelController:
    """Own the dynamic channel-tab lifecycle for one selected job."""

    def __init__(self, bindings: OutputChannelBindings) -> None:
        self.bindings = bindings

    def set_status(self, channel_id: str, key: str) -> None:
        bindings = self.bindings
        label = bindings.status.get(channel_id)
        if label is not None:
            bindings.status_keys[channel_id] = key
            label.SetLabel(f"{t('jobs_outputs.status')}: {t(key)}")

    def ensure_tabs(self, channels: list[ResolvedOutputChannel]) -> None:
        bindings = self.bindings
        state, model = bindings.state, bindings.model
        current_ids = set(bindings.channels)
        new_ids = {channel.id for channel in channels}
        for channel_id in current_ids - new_ids:
            text_control = bindings.channels.pop(channel_id, None)
            for mapping in (
                bindings.paths, bindings.paused, bindings.follow, bindings.pause_buttons,
                bindings.status, bindings.status_keys, bindings.path_labels, bindings.offsets,
                bindings.in_flight, bindings.waiting,
            ):
                mapping.pop(channel_id, None)
            follower = state.get("followers", {}).pop(channel_id, None)
            if follower is not None:
                follower.close()
            try:
                page = text_control.GetParent() if text_control else None
                index = next(
                    (index for index in range(bindings.notebook.GetPageCount())
                     if bindings.notebook.GetPage(index) is page),
                    -1,
                )
                if index >= 0:
                    bindings.notebook.DeletePage(index)
            except Exception:
                pass

        for channel in channels:
            if channel.id in bindings.channels:
                path_field = bindings.paths.get(channel.id)
                if path_field:
                    path_field.SetValue(channel.path)
                follower = state.setdefault("followers", {}).get(channel.id)
                if follower is not None:
                    follower.assign(
                        channel_id=channel.id, job_id=model.selected_job_store.job_id,
                        generation=model.selected_job_store.generation, label=channel.label,
                        path=channel.path,
                        origin="provider" if channel.definition is not None else "legacy_slurm",
                        roles=channel.roles,
                    )
                continue
            self._add_channel(channel)

        if not channels:
            bindings.no_channels_label.Show()
            if bindings.notebook.GetPageCount() == 0:
                bindings.notebook.AddPage(bindings.no_channels_label, t("jobs_outputs.outputs_title"))
        else:
            bindings.no_channels_label.Hide()
            try:
                index = next(
                    (index for index in range(bindings.notebook.GetPageCount())
                     if bindings.notebook.GetPage(index) is bindings.no_channels_label),
                    -1,
                )
                if index >= 0:
                    bindings.notebook.RemovePage(index)
            except Exception:
                pass

    def _add_channel(self, channel: ResolvedOutputChannel) -> None:
        bindings = self.bindings
        wx, state, model = bindings.wx, bindings.state, bindings.model
        panel = wx.Panel(bindings.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)
        toolbar = wx.BoxSizer(wx.HORIZONTAL)
        path_label = wx.StaticText(panel, label=f"{t('jobs_outputs.path')}:")
        path_field = wx.TextCtrl(panel, style=wx.TE_READONLY)
        path_field.SetValue(channel.path)
        pause_button = wx.Button(panel, label=t("jobs.pause_output"), size=(80, -1))
        refresh_button = wx.Button(panel, label=t("jobs.refresh"), size=(70, -1))
        follow_checkbox = wx.CheckBox(panel, label=t("files.auto_scroll"))
        follow_checkbox.SetValue(True)
        status_label = wx.StaticText(
            panel, label=f"{t('jobs_outputs.status')}: {t('jobs_outputs.status_following')}"
        )
        toolbar.Add(path_field, 1, wx.EXPAND | wx.RIGHT, 4)
        toolbar.Insert(0, path_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        toolbar.Add(pause_button, 0, wx.RIGHT, 4)
        toolbar.Add(refresh_button, 0, wx.RIGHT, 4)
        toolbar.Add(follow_checkbox, 0, wx.ALIGN_CENTER_VERTICAL)
        toolbar.AddStretchSpacer(1)
        toolbar.Add(status_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 6)
        text_control = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        text_control.SetMinSize(wx.Size(-1, 150))
        sizer.Add(toolbar, 0, wx.EXPAND | wx.ALL, 4)
        sizer.Add(text_control, 1, wx.EXPAND | wx.ALL, 4)
        panel.SetSizer(sizer)
        bindings.notebook.AddPage(panel, channel.label)

        bindings.channels[channel.id] = text_control
        bindings.paths[channel.id] = path_field
        bindings.paused[channel.id] = False
        bindings.follow[channel.id] = True
        bindings.pause_buttons[channel.id] = pause_button
        bindings.status[channel.id] = status_label
        bindings.status_keys[channel.id] = "jobs_outputs.status_following"
        bindings.path_labels[channel.id] = path_label
        bindings.offsets[channel.id] = 0
        bindings.in_flight[channel.id] = False
        bindings.waiting[channel.id] = 0
        state.setdefault("followers", {})[channel.id] = OutputFollower(OutputFollowerState(
            tracking_id=f"follower-{uuid4().hex}", channel_id=channel.id,
            job_id=model.selected_job_store.job_id,
            generation=model.selected_job_store.generation, label=channel.label,
            path=channel.path,
            origin="provider" if channel.definition is not None else "legacy_slurm",
            roles=channel.roles,
        ))

        def on_pause(_event=None, cid=channel.id, button=pause_button):
            bindings.paused[cid] = not bindings.paused[cid]
            button.SetLabel(t("jobs.resume_output" if bindings.paused[cid] else "jobs.pause_output"))
            self.set_status(
                cid, "jobs_outputs.status_paused" if bindings.paused[cid]
                else "jobs_outputs.status_following",
            )

        def on_refresh(_event=None, cid=channel.id):
            if bindings.refresh_single is not None:
                bindings.refresh_single(cid)

        def on_follow(_event=None, cid=channel.id, checkbox=follow_checkbox):
            bindings.follow[cid] = checkbox.GetValue()

        pause_button.Bind(wx.EVT_BUTTON, on_pause)
        refresh_button.Bind(wx.EVT_BUTTON, on_refresh)
        follow_checkbox.Bind(wx.EVT_CHECKBOX, on_follow)

    def resolve_channels(self) -> list[ResolvedOutputChannel]:
        bindings = self.bindings
        context = bindings.model.selected_job_store.context
        if not context.job_id:
            return []
        state = bindings.state
        provider = state.get("output_channel_defs_provider")
        definitions = provider() if callable(provider) else state.get("output_channel_defs")
        state["output_channel_defs"] = definitions
        resolver_args = {
            "job_id": context.job_id, "workdir": context.workdir,
            "scontrol_stdout": context.stdout_path, "scontrol_stderr": context.stderr_path,
            "script_text": context.script_text, "script_remote_path": context.script_path,
            "job_name": context.name, "language": current_language(),
        }
        if definitions is None:
            channels = bindings.resolver.resolve_legacy(**resolver_args)
        else:
            channels = bindings.resolver.resolve(definitions, **resolver_args)
        for output in state.get("tracked_outputs", []):
            if output.job_id and output.job_id != context.job_id:
                continue
            channels.append(ResolvedOutputChannel(
                id=output.tracking_id, role="manual", label=output.label,
                path=output.path, source="manual", roles=("manual",),
            ))
        return channels
