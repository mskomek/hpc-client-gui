"""wx jobs/output tracking model with live-tail and detached-view contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from threading import Lock, Thread
from typing import Any, Callable

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.services.job_failure_classifier import explain_job_failure
from hpc_gui.services.job_provenance import JobProvenanceCapture
from hpc_gui.services.job_tracking_controller import JobTrackingController


_ANSI = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")


@dataclass(frozen=True)
class DetachedOutput:
    id: str
    stdout_path: str = ""
    stderr_path: str = ""
    mode: str = "combined"
    cols: int = 80
    rows: int = 24


def clean_output(text: str, max_lines: int = 5000) -> str:
    lines = str(text or "").splitlines()[-max(1, int(max_lines)):]
    return _ANSI.sub("", "".join(f"{line}\n" for line in lines))


class WxJobsModel:
    def __init__(self, *, notify: Callable[[str], None] | None = None, provenance: JobProvenanceCapture | None = None, completion_notify: Callable[[str, str], None] | None = None) -> None:
        self.tracking = JobTrackingController()
        self.notify = notify
        self.provenance = provenance
        self.detached: list[DetachedOutput] = []
        self.failure = None
        self.tail_failures = 0
        self.completion_notify = completion_notify
        self._job_states: dict[str, str] = {}

    def poll_allowed(self, details_visible: bool = True, auto_refresh: bool = True) -> bool:
        return self.tracking.should_poll_jobs(details_visible, auto_refresh)

    def set_output(self, stdout_path: str = "", stderr_path: str = "") -> None:
        self.tracking.set_output_metadata(stdout_path=stdout_path, stderr_path=stderr_path)

    def open_detached(self, stdout_path: str = "", stderr_path: str = "", mode: str = "combined") -> DetachedOutput:
        view = DetachedOutput(str(len(self.detached) + 1), stdout_path, stderr_path, mode)
        self.detached.append(view)
        return view

    def update_detached(self, view_id: str, text: str, max_lines: int = 5000) -> str:
        if not any(view.id == str(view_id) for view in self.detached):
            raise KeyError(view_id)
        return clean_output(text, max_lines)

    def resize_detached(self, view_id: str, cols: int, rows: int) -> DetachedOutput:
        for index, view in enumerate(self.detached):
            if view.id == str(view_id):
                resized = DetachedOutput(view.id, view.stdout_path, view.stderr_path, view.mode, max(1, int(cols)), max(1, int(rows)))
                self.detached[index] = resized
                return resized
        raise KeyError(view_id)

    def record_tail_failure(self) -> int:
        self.tail_failures += 1
        return self.tail_failures

    def record_tail_success(self) -> None:
        self.tail_failures = 0

    def cancel_job(self, cancel: Callable[[str], Any], job_id: str) -> Any:
        return cancel(str(job_id)) if str(job_id).strip() else None

    def explain_failure(self, job: Any):
        self.failure = explain_job_failure(job)
        return self.failure

    def submitted(self, job_id: str, script_text: str, **kwargs: Any) -> None:
        if self.provenance:
            self.provenance.submitted(job_id, script_text, **kwargs)
        if self.notify:
            self.notify(str(job_id))

    def update_job_state(self, job_id: str, state: str, message: str = "") -> bool:
        """Publish one completion event per observed terminal state transition."""
        job_id, state = str(job_id).strip(), str(state).strip().upper()
        if not job_id:
            return False
        previous = self._job_states.get(job_id)
        self._job_states[job_id] = state
        if state not in {"COMPLETED", "COMPLETING", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY"}:
            return False
        if previous == state or not self.completion_notify:
            return False
        self.completion_notify(job_id, message or state)
        return True


def show_job_output(parent, model: WxJobsModel, view_id: str, *, read_output=None, interval_ms: int = 1000) -> int:
    """Show a bounded detached output view; polling stays in the callback."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    view = next(item for item in model.detached if item.id == str(view_id))
    frame = wx.Frame(parent, title=f"Job output {view.id}", size=(800, 500))
    output = wx.TextCtrl(frame, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
    timer = wx.Timer(frame)
    state = {"closed": False, "in_flight": False}
    state_lock = Lock()

    def refresh(_event=None):
        if not read_output:
            return
        with state_lock:
            if state["closed"] or state["in_flight"]:
                return
            state["in_flight"] = True

        def fetch() -> None:
            try:
                text = model.update_detached(view.id, read_output())
                wx.CallAfter(apply, text, None)
            except Exception as error:
                wx.CallAfter(apply, "", error)

        def apply(text, error) -> None:
            with state_lock:
                state["in_flight"] = False
                if state["closed"]:
                    return
            if error:
                output.SetValue(str(error))
            else:
                output.SetValue(text)
                output.ShowPosition(output.GetLastPosition())

        Thread(target=fetch, daemon=True).start()

    def resized(_event):
        model.resize_detached(view.id, max(1, output.GetClientSize().width // 8), max(1, output.GetClientSize().height // 16))
        _event.Skip()

    def closed(_event):
        with state_lock:
            state["closed"] = True
        timer.Stop()
        frame.Destroy()

    frame.Bind(wx.EVT_TIMER, refresh, timer)
    frame.Bind(wx.EVT_SIZE, resized)
    frame.Bind(wx.EVT_CLOSE, closed)
    if read_output:
        timer.Start(max(100, int(interval_ms)))
        refresh()
    frame.Show()
    return wx.ID_OK


def show_jobs(parent=None, model: WxJobsModel | None = None, *, list_jobs=None, read_output=None, cancel=None, lifecycle=None) -> int:
    """Create the wx Jobs workspace; callbacks are service adapters, never UI IO."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    model = model or WxJobsModel()
    if lifecycle is not None and model.completion_notify is None:
        model.completion_notify = lambda job_id, message: lifecycle.notify_job(message, job_id=job_id)
    frame = wx.Frame(parent, title=t("jobs.title"), size=(1000, 700))
    panel = wx.Panel(frame)
    root = wx.BoxSizer(wx.VERTICAL)
    splitter = wx.SplitterWindow(panel)
    jobs = wx.ListCtrl(splitter, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
    jobs.InsertColumn(0, t("jobs.job_id"))
    jobs.InsertColumn(1, t("jobs.state"))
    right = wx.Panel(splitter)
    right_sizer = wx.BoxSizer(wx.VERTICAL)
    details = wx.TextCtrl(right, style=wx.TE_MULTILINE | wx.TE_READONLY)
    output_split = wx.SplitterWindow(right)
    stdout = wx.TextCtrl(output_split, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
    stderr = wx.TextCtrl(output_split, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
    output_split.SplitHorizontally(stdout, stderr)
    cancel_button = wx.Button(right, label=t("jobs.cancel"))
    right_sizer.Add(details, 0, wx.EXPAND | wx.ALL, 6)
    right_sizer.Add(output_split, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
    right_sizer.Add(cancel_button, 0, wx.ALIGN_RIGHT | wx.ALL, 6)
    right.SetSizer(right_sizer)
    splitter.SplitVertically(jobs, right, 300)
    splitter.SetMinimumPaneSize(220)
    root.Add(splitter, 1, wx.EXPAND | wx.ALL, 8)
    panel.SetSizer(root)
    state = {"items": [], "selected_job": "", "closed": False, "in_flight": False, "output_in_flight": False}
    state_lock = Lock()
    timer = wx.Timer(frame)

    def render_items(items):
        state["items"] = list(items or [])
        jobs.DeleteAllItems()
        for item in state["items"]:
            job_id = str(item.get("id", item.get("job_id", ""))) if isinstance(item, dict) else str(item)
            job_state = str(item.get("state", "")) if isinstance(item, dict) else ""
            index = jobs.InsertItem(jobs.GetItemCount(), job_id)
            jobs.SetItem(index, 1, job_state)

    def refresh_jobs(_event=None):
        if not list_jobs:
            return
        with state_lock:
            if state["closed"] or state["in_flight"]:
                return
            state["in_flight"] = True

        def fetch():
            try:
                result = list_jobs()
                wx.CallAfter(done, result, None)
            except Exception as error:
                wx.CallAfter(done, (), error)

        def done(result, error):
            with state_lock:
                state["in_flight"] = False
            if not state["closed"]:
                if error:
                    details.SetValue(str(error))
                else:
                    render_items(result)
                    for item in result or ():
                        if isinstance(item, dict):
                            model.update_job_state(item.get("id", item.get("job_id", "")), item.get("state", ""), item.get("name", ""))

        Thread(target=fetch, daemon=True).start()

    def refresh_outputs(_event=None):
        if not read_output:
            return
        with state_lock:
            job_id = state["selected_job"]
            if state["closed"] or state["output_in_flight"] or not job_id:
                return
            state["output_in_flight"] = True

        def fetch():
            try:
                result = read_output(job_id)
                wx.CallAfter(render_outputs, result, None)
            except Exception as error:
                wx.CallAfter(render_outputs, None, error)

        Thread(target=fetch, daemon=True).start()

    def render_outputs(result, error):
        with state_lock:
            state["output_in_flight"] = False
            if state["closed"]:
                return
        if error:
            details.SetValue(str(error))
            return
        if isinstance(result, dict):
            stdout.SetValue(clean_output(result.get("stdout", "")))
            stderr.SetValue(clean_output(result.get("stderr", "")))
        elif isinstance(result, (tuple, list)):
            stdout.SetValue(clean_output(result[0] if result else ""))
            stderr.SetValue(clean_output(result[1] if len(result) > 1 else ""))
        else:
            stdout.SetValue(clean_output(result))
            stderr.SetValue("")

    def select_job(event):
        item = state["items"][event.GetIndex()]
        job_id = str(item.get("id", item.get("job_id", ""))) if isinstance(item, dict) else str(item)
        state["selected_job"] = job_id
        model.tracking.select_job(job_id)
        if isinstance(item, dict):
            model.set_output(item.get("stdout_path", ""), item.get("stderr_path", ""))
            details.SetValue("\n".join(f"{key}: {value}" for key, value in item.items()))

    def cancel_job(_event):
        if cancel and model.tracking.selected_job_id:
            cancel(model.tracking.selected_job_id)

    def close(_event):
        state["closed"] = True
        timer.Stop()
        unsubscribe_language_change(refresh_labels)
        frame.Destroy()

    def refresh_labels(_language=None):
        frame.SetTitle(t("jobs.title"))
        jobs.SetColumn(0, t("jobs.job_id"))
        jobs.SetColumn(1, t("jobs.state"))
        cancel_button.SetLabel(t("jobs.cancel"))

    jobs.Bind(wx.EVT_LIST_ITEM_SELECTED, select_job)
    cancel_button.Bind(wx.EVT_BUTTON, cancel_job)
    def tick(event):
        refresh_jobs(event)
        refresh_outputs(event)

    timer.Start(1000)
    frame.Bind(wx.EVT_TIMER, tick, timer)
    frame.Bind(wx.EVT_CLOSE, close)
    subscribe_language_change(refresh_labels)
    refresh_jobs()
    frame.Show()
    return wx.ID_OK


__all__ = ["DetachedOutput", "WxJobsModel", "clean_output", "show_job_output", "show_jobs"]
