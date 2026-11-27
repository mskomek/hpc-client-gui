"""Register accepted jobs and route their output followers in wx Jobs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from threading import Lock, Thread
from typing import Any, Callable
from uuid import uuid4

from hpc_gui.config import storage
from hpc_gui.jobs.output_workspace import show_job_output
from hpc_gui.services.job_submit_cancel import extract_sbatch_job_id
from hpc_gui.services.output_follower import OutputFollower, OutputFollowerState
from hpc_gui.services.slurm_script_parser import parse_job_name, parse_job_paths


@dataclass
class SubmissionFollowBindings:
    wx: Any
    host: Any
    model: Any
    state: dict[str, Any]
    refresh_jobs: Callable
    refresh_outputs: Callable
    resolve_channels: Callable
    ensure_tabs: Callable
    select_page: Callable
    shell_notebook_select: Callable
    outputs_page: Any
    remote_reader: Callable | None
    remote_statter: Callable | None
    lifecycle: Any
    profile_id: str = ""
    cluster_id: str = ""
    provider_id: str = ""


class JobSubmissionFollow:
    """Keep submitted-job identity and output following in the active wx workspace."""

    def __init__(self, bindings: SubmissionFollowBindings) -> None:
        self.bindings = bindings

    def completed(self, output: str, script_path: str, script_text: str) -> str:
        job_id = extract_sbatch_job_id(output)
        if not job_id:
            return ""
        b = self.bindings
        b.wx.CallAfter(self._register, job_id, str(script_path), str(script_text))
        return job_id

    def _register(self, job_id: str, script_path: str, script_text: str) -> None:
        b = self.bindings
        name = parse_job_name(script_text) or PurePosixPath(script_path).stem
        paths = parse_job_paths(
            script_text,
            script_path,
            job_id=job_id,
            job_name=name,
        )
        context = b.model.selected_job_store.select(
            job_id=job_id,
            profile_id=b.profile_id,
            cluster_id=b.cluster_id,
            provider_id=b.provider_id,
            name=name,
            workdir=paths.workdir,
            workdir_source="submitted_script",
            stdout_path=paths.stdout,
            stderr_path=paths.stderr,
            script_path=script_path,
            script_text=script_text,
            submit_directory=str(PurePosixPath(script_path).parent),
        )
        b.model.tracking.select_job(job_id)
        b.model.set_output(paths.stdout, paths.stderr)
        b.state["selected_job"] = job_id
        b.state["bulk_selected_job_ids"] = {job_id}
        b.state["selected_generation"] = context.generation
        b.state["raw_details_result"] = None
        b.state["raw_accounting_result"] = None
        b.refresh_jobs()

        mode = storage.get_sbatch_follow_mode()
        if mode == storage.SBATCH_FOLLOW_MODE_NONE:
            return
        b.shell_notebook_select()
        if mode in {
            storage.SBATCH_FOLLOW_MODE_OUTPUTS_TAB,
            storage.SBATCH_FOLLOW_MODE_NEW_TABS_SPLIT,
        }:
            b.refresh_outputs(force=True)
            b.ensure_tabs(b.resolve_channels())
            b.select_page(b.outputs_page)
            return
        if mode == storage.SBATCH_FOLLOW_MODE_NEW_WINDOWS_SPLIT:
            self._show_split_windows(job_id, context.generation, paths.stdout, paths.stderr)
            return
        if mode == storage.SBATCH_FOLLOW_MODE_NEW_WINDOW_COMBINED:
            self._show_pair_window(job_id, context.generation, paths.stdout, paths.stderr)

    def _show_split_windows(self, job_id: str, generation: int, stdout: str, stderr: str) -> None:
        b = self.bindings
        for label, path in (("Output", stdout), ("Error", stderr)):
            if not path:
                continue
            follower = self._window_follower(job_id, generation, label, path)
            show_job_output(
                b.host,
                b.model,
                follower.state.tracking_id,
                follower=follower,
                read_path=b.remote_reader,
                stat_path=b.remote_statter,
                lifecycle=b.lifecycle,
            )

    def _show_pair_window(self, job_id: str, generation: int, stdout: str, stderr: str) -> None:
        b = self.bindings
        import wx

        frame = wx.Frame(b.host, title=f"Job {job_id} — Output and Error", size=(900, 600))
        splitter = wx.SplitterWindow(frame)
        controls = []
        followers = []
        for label, path in (("Output", stdout), ("Error", stderr)):
            pane = wx.Panel(splitter)
            sizer = wx.BoxSizer(wx.VERTICAL)
            sizer.Add(wx.StaticText(pane, label=f"{label}: {path}"), 0, wx.EXPAND | wx.ALL, 5)
            text = wx.TextCtrl(pane, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
            sizer.Add(text, 1, wx.EXPAND | wx.ALL, 5)
            pane.SetSizer(sizer)
            controls.append(text)
            followers.append(self._window_follower(job_id, generation, label, path))
            if len(controls) == 1:
                first = pane
            else:
                second = pane
        if len(controls) == 2:
            splitter.SplitHorizontally(first, second)
        elif controls:
            splitter.Initialize(first)
        frame.SetSizer(wx.BoxSizer(wx.VERTICAL))
        frame.GetSizer().Add(splitter, 1, wx.EXPAND)
        frame._wx_output_followers = followers
        frame._wx_output_controls = controls
        timer = wx.Timer(frame)
        state = {"closed": False, "busy": False}
        lock = Lock()

        def refresh(_event=None):
            if not callable(b.remote_reader) or not controls:
                return
            with lock:
                if state["closed"] or state["busy"]:
                    return
                state["busy"] = True

            def worker():
                result = []
                for follower in followers:
                    try:
                        _chunk, content, _waiting = follower.poll(b.remote_reader, b.remote_statter)
                        result.append((content, None))
                    except Exception as error:
                        result.append(("", error))
                wx.CallAfter(apply, result)

            Thread(target=worker, daemon=True).start()

        def apply(result):
            with lock:
                state["busy"] = False
                if state["closed"]:
                    return
            for control, (content, error) in zip(controls, result):
                control.SetValue(str(error) if error else content)

        def close(event=None):
            with lock:
                if state["closed"]:
                    return
                state["closed"] = True
            timer.Stop()
            for follower in followers:
                follower.close()
            if event is None:
                frame.Destroy()
            else:
                event.Skip()

        frame.Bind(wx.EVT_TIMER, refresh, timer)
        frame.Bind(wx.EVT_CLOSE, close)
        if b.lifecycle is not None:
            b.lifecycle.register_cleanup(close)
        timer.Start(1000)
        refresh()
        frame.Show()

    @staticmethod
    def _window_follower(job_id: str, generation: int, label: str, path: str) -> OutputFollower:
        tracking_id = f"submitted-{job_id}-{label.lower()}-{uuid4().hex}"
        return OutputFollower(OutputFollowerState(
            tracking_id=tracking_id,
            channel_id=None,
            job_id=job_id,
            generation=generation,
            label=label,
            path=path,
            origin="manual",
            roles=("manual",),
        ))


def install_submission_callback(
    wx, host, model, state, refresh_jobs, refresh_outputs, resolve_channels,
    ensure_tabs, select_page, outputs_page, kwargs,
    remote_reader=None, remote_statter=None, lifecycle=None,
    profile_id="", cluster_id="", provider_id="",
):
    """Attach the shell-facing callback after the Jobs workspace is composed."""
    session_state = kwargs.get("session_state") or {}

    def select_shell_notebook():
        notebook, page = session_state.get("_embedded_main_notebook"), host
        if notebook is None:
            return
        index = next(
            (item for item in range(notebook.GetPageCount()) if notebook.GetPage(item) is page),
            -1,
        )
        if index >= 0:
            notebook.SetSelection(index)

    bindings = SubmissionFollowBindings(
        wx=wx,
        host=host,
        model=model,
        state=state,
        refresh_jobs=refresh_jobs,
        refresh_outputs=refresh_outputs,
        resolve_channels=resolve_channels,
        ensure_tabs=ensure_tabs,
        select_page=select_page,
        shell_notebook_select=select_shell_notebook,
        outputs_page=outputs_page,
        remote_reader=remote_reader,
        remote_statter=remote_statter,
        lifecycle=lifecycle,
        profile_id=profile_id,
        cluster_id=cluster_id,
        provider_id=provider_id,
    )
    controller = JobSubmissionFollow(bindings)

    host._wx_jobs_submission_completed = controller.completed
    host._wx_jobs_submission_controller = controller
