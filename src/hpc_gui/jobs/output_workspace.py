"""Detached job output model and live output window."""

from __future__ import annotations

import re
from dataclasses import dataclass
from threading import Lock, Thread
from typing import Any, Callable

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.services.job_failure_classifier import explain_job_failure
from hpc_gui.services.job_provenance import JobProvenanceCapture
from hpc_gui.services.job_tracking_controller import JobTrackingController
from hpc_gui.services.selected_job_context import SelectedJobStore

_ANSI = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")


def _format_size(n: int | str) -> str:
    try:
        n = int(n)
    except Exception:
        return ""
    if n <= 0:
        return ""
    units = ["B", "KB", "MB", "GB", "TB"]
    v = float(n)
    i = 0
    while v >= 1024 and i < len(units) - 1:
        v /= 1024.0
        i += 1
    return f"{v:.1f} {units[i]}" if i else f"{int(v)} {units[i]}"


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


def _output_at_bottom(ctrl) -> bool:
    try:
        import wx
        maximum = ctrl.GetScrollRange(wx.VERTICAL)
        return maximum <= 0 or ctrl.GetScrollPos(wx.VERTICAL) >= maximum - 1
    except (AttributeError, RuntimeError, ImportError):
        return True


class WxJobsModel:
    def __init__(self, *, notify: Callable[[str], None] | None = None, provenance: JobProvenanceCapture | None = None, completion_notify: Callable[[str, str], None] | None = None) -> None:
        self.tracking = JobTrackingController()
        self.selected_job_store = SelectedJobStore()
        self.notify = notify
        self.provenance = provenance
        self.detached: list[DetachedOutput] = []
        self.failure = None
        self.tail_failures = 0
        self.completion_notify = completion_notify
        self._job_states: dict[str, str] = {}
        self._active_job_ids: set[str] = set()
        self._monitor_initialized = False
        self._monitor_generation = 0

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
        if state not in {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY"}:
            return False
        if previous == state or not self.completion_notify:
            return False
        if message:
            notification = message
        elif state == "COMPLETED":
            notification = t("login.job_completed").format(jobid=job_id)
        else:
            notification = t("login.job_failed").format(jobid=job_id, state=state)
        self.completion_notify(job_id, notification)
        return True

    def set_monitor_generation(self, generation: int) -> None:
        generation = int(generation)
        if generation == self._monitor_generation:
            return
        self._monitor_generation = generation
        self._active_job_ids.clear()
        self._monitor_initialized = False

    def poll_active_jobs(self, items, final_state=None, *, generation: int | None = None) -> bool:
        """Track squeue membership and query final states for disappeared jobs."""
        if generation is not None and int(generation) != self._monitor_generation:
            return False
        rows = tuple(items or ())
        current = {
            str(item.get("id", item.get("job_id", ""))).strip()
            for item in rows
            if isinstance(item, dict) and str(item.get("id", item.get("job_id", ""))).strip()
        }
        if not self._monitor_initialized:
            self._active_job_ids = current
            self._monitor_initialized = True
            for item in rows:
                if isinstance(item, dict):
                    self._job_states[str(item.get("id", item.get("job_id", "")))] = str(item.get("state", "")).strip().upper()
            return True
        for job_id in sorted(self._active_job_ids - current):
            state = str(final_state(job_id) if final_state else "").strip().upper()
            if state in {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY"}:
                self.update_job_state(job_id, state)
            elif self.completion_notify:
                self.completion_notify(job_id, t("login.job_finished").format(jobid=job_id))
        for item in rows:
            if isinstance(item, dict):
                self.update_job_state(item.get("id", item.get("job_id", "")), item.get("state", ""), "")
        self._active_job_ids = current
        return True


def show_job_output(parent, model: WxJobsModel, view_id: str, *, read_output=None, read_path=None, stat_path=None, follower=None, interval_ms: int = 1000, lifecycle=None, on_closed=None) -> int:
    """Show a live detached follower; late callbacks are ignored after close."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    view = next((item for item in model.detached if item.id == str(view_id)), None)
    frame = wx.Frame(parent, title=f"{t('jobs.open_output')} {view.id if view else view_id}", size=(800, 500))
    root = wx.BoxSizer(wx.VERTICAL)
    if follower is not None:
        root.Add(wx.StaticText(frame, label=follower.state.path), 0, wx.EXPAND | wx.ALL, 6)
    output = wx.TextCtrl(frame, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
    root.Add(output, 1, wx.EXPAND | wx.ALL, 6)
    controls = wx.BoxSizer(wx.HORIZONTAL)
    pause = wx.Button(frame, label=t("jobs.pause_output"))
    auto_scroll = wx.CheckBox(frame, label=t("files.auto_scroll"))
    auto_scroll.SetValue(True)
    controls.Add(pause, 0, wx.RIGHT, 6)
    controls.Add(auto_scroll, 0, wx.ALIGN_CENTER_VERTICAL)
    root.Add(controls, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
    frame.SetSizer(root)
    frame._wx_output_controls = {"output": output, "pause": pause, "auto_scroll": auto_scroll, "follower": follower}
    timer = wx.Timer(frame)
    state = {"closed": False, "in_flight": False, "at_bottom": True}
    state_lock = Lock()

    def toggle_pause(_event=None):
        paused = follower is not None and follower.state.paused
        if follower is not None:
            follower.state.paused = not paused
        pause.SetLabel(
            t("jobs.resume_output") if follower is not None and follower.state.paused
            else t("jobs.pause_output")
        )

    def refresh(_event=None):
        if follower is None and not read_output:
            return
        state["at_bottom"] = _output_at_bottom(output)
        with state_lock:
            if state["closed"] or state["in_flight"]:
                return
            state["in_flight"] = True
            if follower is not None:
                follower.state.paused = pause.GetLabel() == t("jobs.resume_output")
                follower.state.auto_scroll = auto_scroll.GetValue()

        def fetch() -> None:
            try:
                if follower is not None:
                    if not callable(read_path):
                        raise RuntimeError(t("jobs_outputs.remote_reader_unavailable"))
                    _chunk, text, _waiting = follower.poll(read_path, stat_path)
                else:
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
                if auto_scroll.GetValue() and state["at_bottom"]:
                    output.ShowPosition(output.GetLastPosition())

        Thread(target=fetch, daemon=True).start()

    pause.Bind(wx.EVT_BUTTON, toggle_pause)

    def resized(_event):
        if view is not None:
            model.resize_detached(view.id, max(1, output.GetClientSize().width // 8), max(1, output.GetClientSize().height // 16))
        _event.Skip()

    def closed(_event=None):
        with state_lock:
            if state["closed"]:
                return
            state["closed"] = True
        if follower is not None:
            follower.close()
        timer.Stop()
        unsubscribe_language_change(refresh_labels)
        if callable(on_closed):
            on_closed()
        frame.Destroy()

    def refresh_labels(_language=None):
        frame.SetTitle(f"{t('jobs.open_output')} {view.id if view else view_id}")

    frame._wx_output_refresh = refresh
    frame.Bind(wx.EVT_TIMER, refresh, timer)
    frame.Bind(wx.EVT_SIZE, resized)
    frame.Bind(wx.EVT_CLOSE, closed)
    subscribe_language_change(refresh_labels)
    if lifecycle is not None:
        lifecycle.register_cleanup(closed)
    if follower is not None or read_output:
        timer.Start(max(100, int(interval_ms)))
        refresh()
    frame.Show()
    return wx.ID_OK
