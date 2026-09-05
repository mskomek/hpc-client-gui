"""wx jobs/output tracking model with live-tail and detached-view contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from threading import Lock, Thread
from types import SimpleNamespace
from typing import Any, Callable

from hpc_gui.core.i18n import subscribe_language_change, t, unsubscribe_language_change
from hpc_gui.services.job_failure_classifier import explain_job_failure
from hpc_gui.services.job_provenance import JobProvenanceCapture
from hpc_gui.services.job_tracking_controller import JobTrackingController
from hpc_gui.wx_host import make_host


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


def show_job_output(parent, model: WxJobsModel, view_id: str, *, read_output=None, interval_ms: int = 1000, lifecycle=None) -> int:
    """Show a bounded detached output view; polling stays in the callback."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    view = next(item for item in model.detached if item.id == str(view_id))
    frame = wx.Frame(parent, title=f"{t('jobs.open_output')} {view.id}", size=(800, 500))
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

    def closed(_event=None):
        with state_lock:
            state["closed"] = True
        timer.Stop()
        unsubscribe_language_change(refresh_labels)
        frame.Destroy()

    def refresh_labels(_language=None):
        frame.SetTitle(f"{t('jobs.open_output')} {view.id}")

    frame.Bind(wx.EVT_TIMER, refresh, timer)
    frame.Bind(wx.EVT_SIZE, resized)
    frame.Bind(wx.EVT_CLOSE, closed)
    subscribe_language_change(refresh_labels)
    if lifecycle is not None:
        lifecycle.register_cleanup(closed)
    if read_output:
        timer.Start(max(100, int(interval_ms)))
        refresh()
    frame.Show()
    return wx.ID_OK


def _build_jobs(parent, model: WxJobsModel | None, *, list_jobs, read_output, cancel, lifecycle, final_state, generation, embedded, refresh_sacct=None, show_job_details=None, refresh_lssrv=None, list_job_files=None, **kwargs):
    """Create the wx Jobs workspace; callbacks are service adapters, never UI IO."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    # Alias tolerance for caller naming
    if refresh_sacct is None:
        refresh_sacct = kwargs.get("sacct") or kwargs.get("sacct_callback") or kwargs.get("refresh_accounting")
    if show_job_details is None:
        show_job_details = kwargs.get("show_details") or kwargs.get("scontrol") or kwargs.get("scontrol_show_job") or kwargs.get("show_details_callback")
    if refresh_lssrv is None:
        refresh_lssrv = kwargs.get("lssrv") or kwargs.get("lssrv_refresh") or kwargs.get("lssrv_callback") or kwargs.get("refresh_lssrv_callback")
    if list_job_files is None:
        list_job_files = kwargs.get("list_job_files") or kwargs.get("job_files") or kwargs.get("files_callback")
    if refresh_sacct is None and "refresh_sacct" in kwargs:
        refresh_sacct = kwargs["refresh_sacct"]
    if show_job_details is None and "show_job_details" in kwargs:
        show_job_details = kwargs["show_job_details"]
    if refresh_lssrv is None and "refresh_lssrv" in kwargs:
        refresh_lssrv = kwargs["refresh_lssrv"]
    if list_job_files is None and "list_job_files" in kwargs:
        list_job_files = kwargs["list_job_files"]
    model = model or WxJobsModel()
    if lifecycle is not None and model.completion_notify is None:
        model.completion_notify = lambda job_id, message: lifecycle.notify_job(message, job_id=job_id)
    host, finish = make_host(parent, title=t("jobs.title"), size=(1000, 700), embedded=embedded)
    panel = wx.Panel(host)
    root = wx.BoxSizer(wx.VERTICAL)
    # Sub-tab strip with three pages
    notebook = wx.Notebook(panel)
    details_page = wx.Panel(notebook)
    files_page = wx.Panel(notebook)
    outputs_page = wx.Panel(notebook)
    # Keep tab labels via i18n; first tab is Jobs / Details
    notebook.AddPage(details_page, f"{t('jobs.title')} / {t('common.details')}")
    notebook.AddPage(files_page, t("jobs_outputs.files_title"))
    notebook.AddPage(outputs_page, t("jobs_outputs.outputs_title"))
    # --- Details page layout: existing job list + output + two new groups ---
    details_sizer = wx.BoxSizer(wx.VERTICAL)
    splitter = wx.SplitterWindow(details_page)
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
    try:
        output_row = wx.WrapSizer(wx.HORIZONTAL)
    except Exception:
        output_row = wx.BoxSizer(wx.HORIZONTAL)
    refresh_button = wx.Button(right, label=t("jobs.refresh"))
    follow = wx.CheckBox(right, label=t("files.auto_scroll"))
    detached_button = wx.Button(right, label=t("jobs.open_output"))
    pause_button = wx.Button(right, label=t("jobs.pause_output"))
    follow.SetValue(True)
    output_row.Add(refresh_button, 0, wx.RIGHT, 6)
    output_row.Add(detached_button, 0, wx.RIGHT, 6)
    output_row.Add(pause_button, 0, wx.RIGHT, 6)
    output_row.Add(follow, 0, wx.ALIGN_CENTER_VERTICAL)
    cancel_button = wx.Button(right, label=t("jobs.cancel"))
    try:
        cancel_row = wx.WrapSizer(wx.HORIZONTAL)
    except Exception:
        cancel_row = wx.BoxSizer(wx.HORIZONTAL)
    cancel_row.AddStretchSpacer(1)
    cancel_row.Add(cancel_button, 0, wx.ALIGN_CENTER_VERTICAL)
    right_sizer.Add(details, 0, wx.EXPAND | wx.ALL, 6)
    right_sizer.Add(output_split, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
    right_sizer.Add(output_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
    right_sizer.Add(cancel_row, 0, wx.EXPAND | wx.ALL, 6)
    right.SetSizer(right_sizer)
    splitter.SplitVertically(jobs, right, 300)
    splitter.SetMinimumPaneSize(220)
    details_sizer.Add(splitter, 1, wx.EXPAND | wx.ALL, 8)
    # Accounting & Job Details group
    accounting_box = wx.StaticBox(details_page, label=t("jobs_outputs.accounting_details"))
    accounting_sizer = wx.StaticBoxSizer(accounting_box, wx.VERTICAL)
    try:
        accounting_row = wx.WrapSizer(wx.HORIZONTAL)
    except Exception:
        accounting_row = wx.BoxSizer(wx.HORIZONTAL)
    sacct_button = wx.Button(accounting_box, label=t("jobs_outputs.refresh_sacct"))
    job_id_field = wx.TextCtrl(accounting_box, style=wx.TE_PROCESS_ENTER)
    try:
        job_id_field.SetHint(t("jobs.job_id"))
    except Exception:
        pass
    show_details_button = wx.Button(accounting_box, label=t("jobs_outputs.show_job_details"))
    accounting_row.Add(sacct_button, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)
    accounting_row.Add(job_id_field, 1, wx.RIGHT | wx.EXPAND, 6)
    accounting_row.Add(show_details_button, 0, wx.ALIGN_CENTER_VERTICAL, 6)
    accounting_sizer.Add(accounting_row, 0, wx.EXPAND | wx.ALL, 6)
    accounting_text = wx.TextCtrl(accounting_box, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
    try:
        accounting_text.SetHint(t("jobs_outputs.accounting_placeholder"))
    except Exception:
        pass
    accounting_sizer.Add(accounting_text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
    accounting_sizer.SetMinSize(wx.Size(-1, 90))
    details_sizer.Add(accounting_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    # Cluster Servers (lssrv) group
    lssrv_box = wx.StaticBox(details_page, label=t("jobs_outputs.lssrv_title"))
    lssrv_sizer = wx.StaticBoxSizer(lssrv_box, wx.VERTICAL)
    try:
        lssrv_row = wx.WrapSizer(wx.HORIZONTAL)
    except Exception:
        lssrv_row = wx.BoxSizer(wx.HORIZONTAL)
    lssrv_button = wx.Button(lssrv_box, label=t("jobs_outputs.lssrv_refresh"))
    lssrv_row.Add(lssrv_button, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)
    lssrv_row.AddStretchSpacer(1)
    lssrv_sizer.Add(lssrv_row, 0, wx.EXPAND | wx.ALL, 6)
    lssrv_text = wx.TextCtrl(lssrv_box, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
    try:
        lssrv_text.SetHint(t("jobs_outputs.lssrv_empty"))
    except Exception:
        pass
    lssrv_sizer.Add(lssrv_text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
    lssrv_sizer.SetMinSize(wx.Size(-1, 90))
    details_sizer.Add(lssrv_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    details_page.SetSizer(details_sizer)
    # --- Files sub-tab: real datasource (job files) ---
    files_sizer = wx.BoxSizer(wx.VERTICAL)
    files_toolbar = wx.BoxSizer(wx.HORIZONTAL)
    files_refresh = wx.Button(files_page, label=t("jobs.refresh"))
    files_toolbar.Add(files_refresh, 0, wx.RIGHT, 6)
    files_toolbar.AddStretchSpacer(1)
    files_sizer.Add(files_toolbar, 0, wx.EXPAND | wx.ALL, 4)
    job_files = wx.ListCtrl(files_page, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
    job_files.InsertColumn(0, t("dirs.col_name"))
    job_files.InsertColumn(1, t("dirs.col_size"))
    job_files.InsertColumn(2, t("jobs_outputs.file"))
    files_sizer.Add(job_files, 1, wx.EXPAND | wx.ALL, 6)
    files_page.SetSizer(files_sizer)
    # --- Outputs sub-tab: real stdout/stderr with follow ---
    outputs_sizer = wx.BoxSizer(wx.VERTICAL)
    outputs_toolbar = wx.BoxSizer(wx.HORIZONTAL)
    outputs_refresh = wx.Button(outputs_page, label=t("jobs.refresh"))
    outputs_follow = wx.CheckBox(outputs_page, label=t("files.auto_scroll"))
    outputs_follow.SetValue(True)
    outputs_pause = wx.Button(outputs_page, label=t("jobs.pause_output"))
    outputs_toolbar.Add(outputs_refresh, 0, wx.RIGHT, 6)
    outputs_toolbar.Add(outputs_pause, 0, wx.RIGHT, 6)
    outputs_toolbar.Add(outputs_follow, 0, wx.ALIGN_CENTER_VERTICAL)
    outputs_toolbar.AddStretchSpacer(1)
    outputs_sizer.Add(outputs_toolbar, 0, wx.EXPAND | wx.ALL, 4)
    outputs_split = wx.SplitterWindow(outputs_page)
    outputs_stdout = wx.TextCtrl(outputs_split, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
    outputs_stderr = wx.TextCtrl(outputs_split, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
    outputs_split.SplitHorizontally(outputs_stdout, outputs_stderr)
    outputs_sizer.Add(outputs_split, 1, wx.EXPAND | wx.ALL, 6)
    outputs_page.SetSizer(outputs_sizer)
    root.Add(notebook, 1, wx.EXPAND | wx.ALL, 8)
    panel.SetSizer(root)
    # Initial enable state: disabled when no callback
    if not refresh_sacct:
        sacct_button.Enable(False)
    if not show_job_details:
        show_details_button.Enable(False)
    if not refresh_lssrv:
        lssrv_button.Enable(False)
    state = {"items": [], "selected_job": "", "closed": False, "in_flight": False, "output_in_flight": False, "cancel_in_flight": False, "user_paused": False, "minimized": False, "follow_calls": 0, "sacct_in_flight": False, "details_in_flight": False, "lssrv_in_flight": False, "files_in_flight": False, "outputs_in_flight": False, "files_generation": 0, "outputs_generation": 0, "outputs_paused": False}
    state_lock = Lock()
    timer = wx.Timer(host)

    def post(callback, *args):
        try:
            if wx.GetApp() is not None:
                wx.CallAfter(callback, *args)
        except BaseException:
            pass

    def render_items(items):
        state["items"] = list(items or [])
        jobs.DeleteAllItems()
        for item in state["items"]:
            job_id = str(item.get("id", item.get("job_id", ""))) if isinstance(item, dict) else str(item)
            job_state = str(item.get("state", "")) if isinstance(item, dict) else ""
            index = jobs.InsertItem(jobs.GetItemCount(), job_id)
            jobs.SetItem(index, 1, job_state)

    def refresh_jobs(_event=None):
        if not list_jobs or state["minimized"]:
            return
        request_generation = generation() if generation else None
        if request_generation is not None:
            model.set_monitor_generation(request_generation)
        with state_lock:
            if state["closed"] or state["in_flight"]:
                return
            state["in_flight"] = True

        def fetch():
            try:
                result = list_jobs()
                post(done, result, None, request_generation)
            except Exception as error:
                post(done, (), error, request_generation)

        def done(result, error, request_generation=None):
            with state_lock:
                state["in_flight"] = False
            if not state["closed"] and (generation is None or request_generation == generation()):
                if error:
                    details.SetValue(str(error))
                else:
                    items = tuple(result or ())
                    render_items(items)
                    for item in items:
                        if isinstance(item, dict):
                            job_id = str(item.get("id", item.get("job_id", ""))).strip()
                            model._job_states.setdefault(job_id, str(item.get("state", "")).strip().upper())
                    model.poll_active_jobs(items, final_state, generation=request_generation)

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
                wx.CallAfter(render_outputs, result, None, job_id)
            except Exception as error:
                wx.CallAfter(render_outputs, None, error, job_id)

        Thread(target=fetch, daemon=True).start()

    def render_outputs(result, error, request_job_id=""):
        with state_lock:
            state["output_in_flight"] = False
            if state["closed"]:
                return
            stale = request_job_id and request_job_id != state["selected_job"]
        if stale:
            refresh_outputs()
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
        if follow.GetValue() and not state["user_paused"] and not state["minimized"]:
            state["follow_calls"] += 1
            stdout.ShowPosition(stdout.GetLastPosition())
            stderr.ShowPosition(stderr.GetLastPosition())

    def toggle_pause(_event=None):
        state["user_paused"] = not state["user_paused"]
        pause_button.SetLabel(t("jobs.resume_output" if state["user_paused"] else "jobs.pause_output"))

    def iconized(event):
        state["minimized"] = bool(event.IsIconized())
        if not state["minimized"]:
            refresh_jobs()
        event.Skip()

    def select_job(event):
        item = state["items"][event.GetIndex()]
        job_id = str(item.get("id", item.get("job_id", ""))) if isinstance(item, dict) else str(item)
        state["selected_job"] = job_id
        model.tracking.select_job(job_id)
        if isinstance(item, dict):
            model.set_output(item.get("stdout_path", ""), item.get("stderr_path", ""))
            lines = [f"{key}: {value}" for key, value in item.items()]
            failure = model.explain_failure(SimpleNamespace(**item))
            if failure:
                lines.extend(failure.as_lines())
            details.SetValue("\n".join(lines))
        refresh_outputs()
        # also refresh Files and Outputs sub-tabs for selected job
        refresh_job_files()
        refresh_outputs_tab()
        # update job_id field for accounting
        try:
            job_id_field.SetValue(job_id)
        except Exception:
            pass

    def cancel_job(_event):
        job_id = model.tracking.selected_job_id
        if not cancel or not job_id or state["cancel_in_flight"]:
            return
        if wx.MessageBox(t("jobs.cancel_confirm").format(job_id=job_id), t("jobs.cancel"), wx.YES_NO | wx.ICON_WARNING) != wx.YES:
            return
        state["cancel_in_flight"] = True
        cancel_button.Enable(False)

        def worker():
            try:
                cancel(job_id)
                wx.CallAfter(cancel_done, None)
            except Exception as error:
                wx.CallAfter(cancel_done, error)

        def cancel_done(error):
            state["cancel_in_flight"] = False
            if state["closed"]:
                return
            cancel_button.Enable(True)
            if error:
                details.SetValue(str(error))

        Thread(target=worker, daemon=True).start()

    def _refresh_sacct(_event=None):
        if not refresh_sacct:
            return
        with state_lock:
            if state["closed"] or state["sacct_in_flight"]:
                return
            state["sacct_in_flight"] = True
        sacct_button.Enable(False)

        def worker():
            try:
                result = refresh_sacct()
                wx.CallAfter(_done, result, None)
            except Exception as error:
                wx.CallAfter(_done, "", error)

        def _done(result, error):
            with state_lock:
                state["sacct_in_flight"] = False
            if state["closed"]:
                return
            sacct_button.Enable(True if refresh_sacct else False)
            if error:
                accounting_text.SetValue(str(error))
            else:
                text = clean_output(result) if result is not None else ""
                # keep placeholder visible if empty via SetValue empty
                accounting_text.SetValue(text)
                if not text:
                    # ensure placeholder hint visible; leave value empty
                    pass

        Thread(target=worker, daemon=True).start()

    def _show_job_details(_event=None):
        if not show_job_details:
            return
        job_id = job_id_field.GetValue().strip() or state["selected_job"] or model.tracking.selected_job_id
        if not job_id:
            accounting_text.SetValue(t("jobs_outputs.job_id_required"))
            return
        with state_lock:
            if state["closed"] or state["details_in_flight"]:
                return
            state["details_in_flight"] = True
        show_details_button.Enable(False)

        def worker():
            try:
                # callback may expect job_id arg or no arg
                try:
                    result = show_job_details(job_id)
                except TypeError:
                    result = show_job_details()
                wx.CallAfter(_done, result, None)
            except Exception as error:
                wx.CallAfter(_done, "", error)

        def _done(result, error):
            with state_lock:
                state["details_in_flight"] = False
            if state["closed"]:
                return
            show_details_button.Enable(True if show_job_details else False)
            if error:
                accounting_text.SetValue(str(error))
            else:
                text = clean_output(result) if result is not None and not isinstance(result, dict) else str(result or "")
                if isinstance(result, dict) and result:
                    # if dict, dump? but unlikely
                    text = "\n".join(f"{k}: {v}" for k, v in result.items())
                accounting_text.SetValue(text)

        Thread(target=worker, daemon=True).start()

    def _refresh_lssrv(_event=None):
        if not refresh_lssrv:
            return
        with state_lock:
            if state["closed"] or state["lssrv_in_flight"]:
                return
            state["lssrv_in_flight"] = True
        lssrv_button.Enable(False)

        def worker():
            try:
                result = refresh_lssrv()
                wx.CallAfter(_done, result, None)
            except Exception as error:
                wx.CallAfter(_done, "", error)

        def _done(result, error):
            with state_lock:
                state["lssrv_in_flight"] = False
            if state["closed"]:
                return
            lssrv_button.Enable(True if refresh_lssrv else False)
            if error:
                lssrv_text.SetValue(t("jobs_outputs.lssrv_failed"))
            else:
                text = str(result or "").strip()
                if not text:
                    lssrv_text.SetValue(t("jobs_outputs.lssrv_empty"))
                else:
                    lssrv_text.SetValue(clean_output(result))

        Thread(target=worker, daemon=True).start()

    def refresh_job_files(_event=None):
        if not list_job_files:
            return
        with state_lock:
            job_id = state["selected_job"]
            if state["closed"] or not job_id:
                return
            state["files_in_flight"] = True
            state["files_generation"] += 1
            gen = state["files_generation"]
            request_id = job_id
        files_refresh.Enable(False)
        def worker(req_id=request_id, g=gen):
            try:
                entries = list_job_files(req_id)
                post(lambda: _done_files(entries, None, req_id, g))
            except Exception as err:
                post(lambda: _done_files([], err, req_id, g))
        def _done_files(entries, err, req_id, g):
            with state_lock:
                state["files_in_flight"] = False
                if state["closed"] or g != state["files_generation"] or req_id != state["selected_job"]:
                    files_refresh.Enable(True)
                    return
            files_refresh.Enable(True)
            if err:
                job_files.DeleteAllItems()
                # show error as single row
                idx = job_files.InsertItem(job_files.GetItemCount(), str(err))
                return
            job_files.DeleteAllItems()
            for entry in entries or []:
                # entry may be dict or object with name/size/path
                if isinstance(entry, dict):
                    name = str(entry.get("name", entry.get("path", ""))).rsplit("/",1)[-1]
                    size = str(entry.get("size", ""))
                    path = str(entry.get("path", name))
                else:
                    name = str(getattr(entry, "name", getattr(entry, "path", ""))).rsplit("/",1)[-1]
                    size = str(getattr(entry, "size", ""))
                    path = str(getattr(entry, "path", name))
                idx = job_files.InsertItem(job_files.GetItemCount(), name)
                job_files.SetItem(idx, 1, size)
                job_files.SetItem(idx, 2, path)
        Thread(target=worker, daemon=True).start()

    def refresh_outputs_tab(_event=None):
        if not read_output:
            return
        with state_lock:
            job_id = state["selected_job"]
            if state["closed"] or not job_id or state["outputs_paused"]:
                return
            state["outputs_in_flight"] = True
            state["outputs_generation"] += 1
            gen = state["outputs_generation"]
            request_id = job_id
        outputs_refresh.Enable(False)
        def worker(req_id=request_id, g=gen):
            try:
                result = read_output(req_id)
                post(lambda: _done_outputs(result, None, req_id, g))
            except Exception as err:
                post(lambda: _done_outputs(None, err, req_id, g))
        def _done_outputs(result, err, req_id, g):
            with state_lock:
                state["outputs_in_flight"] = False
                if state["closed"] or g != state["outputs_generation"] or req_id != state["selected_job"]:
                    outputs_refresh.Enable(True)
                    return
            outputs_refresh.Enable(True)
            if err:
                outputs_stdout.SetValue(str(err))
                outputs_stderr.SetValue("")
                return
            if isinstance(result, dict):
                outputs_stdout.SetValue(clean_output(result.get("stdout","")))
                outputs_stderr.SetValue(clean_output(result.get("stderr","")))
            elif isinstance(result, (tuple,list)):
                outputs_stdout.SetValue(clean_output(result[0] if result else ""))
                outputs_stderr.SetValue(clean_output(result[1] if len(result)>1 else ""))
            else:
                outputs_stdout.SetValue(clean_output(result))
                outputs_stderr.SetValue("")
            if outputs_follow.GetValue() and not state["outputs_paused"] and not state["minimized"]:
                outputs_stdout.ShowPosition(outputs_stdout.GetLastPosition())
                outputs_stderr.ShowPosition(outputs_stderr.GetLastPosition())
        Thread(target=worker, daemon=True).start()

    def toggle_outputs_pause(_event=None):
        state["outputs_paused"] = not state["outputs_paused"]
        outputs_pause.SetLabel(t("jobs.resume_output" if state["outputs_paused"] else "jobs.pause_output"))

    def open_detached(_event):
        job_id = state["selected_job"]
        if not read_output or not job_id:
            return
        view = model.open_detached()

        def read_stdout():
            result = read_output(job_id)
            if isinstance(result, dict):
                return result.get("stdout", "")
            if isinstance(result, (tuple, list)):
                return result[0] if result else ""
            return result

        show_job_output(host, model, view.id, read_output=read_stdout, lifecycle=lifecycle)

    def close(_event=None):
        if state["closed"]:
            return
        state["closed"] = True
        timer.Stop()
        unsubscribe_language_change(refresh_labels)
        host.Hide()
        host.Destroy()

    def refresh_labels(_language=None):
        host.set_host_title(t("jobs.title"))
        jobs.SetColumn(0, t("jobs.job_id"))
        jobs.SetColumn(1, t("jobs.state"))
        refresh_button.SetLabel(t("jobs.refresh"))
        detached_button.SetLabel(t("jobs.open_output"))
        follow.SetLabel(t("files.auto_scroll"))
        cancel_button.SetLabel(t("jobs.cancel"))
        pause_button.SetLabel(t("jobs.resume_output" if state["user_paused"] else "jobs.pause_output"))
        # notebook and groups
        try:
            notebook.SetPageText(0, f"{t('jobs.title')} / {t('common.details')}")
            notebook.SetPageText(1, t("jobs_outputs.files_title"))
            notebook.SetPageText(2, t("jobs_outputs.outputs_title"))
        except Exception:
            pass
        try:
            accounting_box.SetLabel(t("jobs_outputs.accounting_details"))
        except Exception:
            pass
        sacct_button.SetLabel(t("jobs_outputs.refresh_sacct"))
        show_details_button.SetLabel(t("jobs_outputs.show_job_details"))
        try:
            job_id_field.SetHint(t("jobs.job_id"))
        except Exception:
            pass
        try:
            accounting_text.SetHint(t("jobs_outputs.accounting_placeholder"))
        except Exception:
            pass
        try:
            lssrv_box.SetLabel(t("jobs_outputs.lssrv_title"))
        except Exception:
            pass
        lssrv_button.SetLabel(t("jobs_outputs.lssrv_refresh"))
        try:
            lssrv_text.SetHint(t("jobs_outputs.lssrv_empty"))
        except Exception:
            pass
        try:
            job_files.SetColumn(0, t("dirs.col_name"))
            job_files.SetColumn(1, t("dirs.col_size"))
            job_files.SetColumn(2, t("jobs_outputs.file"))
        except Exception:
            pass
        try:
            files_refresh.SetLabel(t("jobs.refresh"))
        except Exception:
            pass
        try:
            outputs_refresh.SetLabel(t("jobs.refresh"))
            outputs_follow.SetLabel(t("files.auto_scroll"))
            outputs_pause.SetLabel(t("jobs.resume_output" if state["outputs_paused"] else "jobs.pause_output"))
        except Exception:
            pass
        if not lssrv_text.GetValue():
            try:
                lssrv_text.SetHint(t("jobs_outputs.lssrv_empty"))
            except Exception:
                pass

    def select_job_wrapper(event):
        select_job(event)
        try:
            job_id_field.SetValue(state.get("selected_job", ""))
        except Exception:
            pass
    jobs.Bind(wx.EVT_LIST_ITEM_SELECTED, select_job_wrapper)
    refresh_button.Bind(wx.EVT_BUTTON, refresh_jobs)
    detached_button.Bind(wx.EVT_BUTTON, open_detached)
    pause_button.Bind(wx.EVT_BUTTON, toggle_pause)
    cancel_button.Bind(wx.EVT_BUTTON, cancel_job)
    sacct_button.Bind(wx.EVT_BUTTON, _refresh_sacct)
    show_details_button.Bind(wx.EVT_BUTTON, _show_job_details)
    lssrv_button.Bind(wx.EVT_BUTTON, _refresh_lssrv)
    files_refresh.Bind(wx.EVT_BUTTON, refresh_job_files)
    outputs_refresh.Bind(wx.EVT_BUTTON, refresh_outputs_tab)
    outputs_pause.Bind(wx.EVT_BUTTON, toggle_outputs_pause)
    # notebook page change triggers refresh of visible tab
    def _on_notebook_page_changed(evt):
        try:
            sel = notebook.GetSelection()
            idx_files = 1
            idx_outputs = 2
            if sel == idx_files:
                refresh_job_files()
            elif sel == idx_outputs:
                refresh_outputs_tab()
        except Exception:
            pass
        evt.Skip()
    notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, _on_notebook_page_changed)
    # also allow Enter in job_id_field to trigger show details
    try:
        job_id_field.Bind(wx.EVT_TEXT_ENTER, _show_job_details)
    except Exception:
        pass
    def tick(event):
        refresh_jobs(event)
        refresh_outputs(event)
        # also poll outputs tab if visible and follow
        try:
            if notebook.GetSelection() == 2:
                refresh_outputs_tab(event)
        except Exception:
            pass
        # poll files tab if visible
        try:
            if notebook.GetSelection() == 1:
                # files tab auto-refresh not needed, but ensure stale handling
                pass
        except Exception:
            pass

    timer.Start(1000)
    host.Bind(wx.EVT_TIMER, tick, timer)
    host.Bind(wx.EVT_ICONIZE, iconized)
    host.bind_host_close(close)
    if lifecycle is not None:
        lifecycle.register_cleanup(host.Hide)
        lifecycle.register_cleanup(close)
    subscribe_language_change(refresh_labels)
    host._wx_jobs_state = state
    host._wx_jobs_controls = {"jobs": jobs, "stdout": stdout, "stderr": stderr, "follow": follow, "pause": pause_button, "refresh": refresh_button, "cancel": cancel_button, "notebook": notebook, "details_page": details_page, "files_page": files_page, "outputs_page": outputs_page, "accounting_text": accounting_text, "job_id_field": job_id_field, "sacct_button": sacct_button, "show_details_button": show_details_button, "lssrv_text": lssrv_text, "lssrv_button": lssrv_button, "lssrv_box": lssrv_box, "accounting_box": accounting_box, "job_files": job_files, "files_refresh": files_refresh, "outputs_stdout": outputs_stdout, "outputs_stderr": outputs_stderr, "outputs_refresh": outputs_refresh, "outputs_follow": outputs_follow, "outputs_pause": outputs_pause}
    host._wx_jobs_refresh_jobs = refresh_jobs
    host._wx_jobs_refresh_outputs = refresh_outputs
    host._wx_jobs_refresh_sacct = _refresh_sacct
    host._wx_jobs_show_details = _show_job_details
    host._wx_jobs_refresh_lssrv = _refresh_lssrv
    host._wx_jobs_notebook = notebook
    host._wx_jobs_refresh_files = refresh_job_files
    host._wx_jobs_refresh_outputs_tab = refresh_outputs_tab
    refresh_jobs()
    finish()
    return host


def build_jobs_panel(parent, model: WxJobsModel | None = None, *, list_jobs=None, read_output=None, cancel=None, lifecycle=None, final_state=None, generation=None, refresh_sacct=None, show_job_details=None, refresh_lssrv=None, **kwargs):
    """Embedded panel factory. Returns the wx.Panel host."""
    # alias handling
    if refresh_sacct is None:
        refresh_sacct = kwargs.get("refresh_sacct") or kwargs.get("sacct")
    if show_job_details is None:
        show_job_details = kwargs.get("show_job_details") or kwargs.get("show_details") or kwargs.get("scontrol")
    if refresh_lssrv is None:
        refresh_lssrv = kwargs.get("refresh_lssrv") or kwargs.get("lssrv")
    return _build_jobs(parent, model, list_jobs=list_jobs, read_output=read_output, cancel=cancel, lifecycle=lifecycle, final_state=final_state, generation=generation, embedded=True, refresh_sacct=refresh_sacct, show_job_details=show_job_details, refresh_lssrv=refresh_lssrv, **kwargs)


def show_jobs(parent=None, model: WxJobsModel | None = None, *, list_jobs=None, read_output=None, cancel=None, lifecycle=None, final_state=None, generation=None, refresh_sacct=None, show_job_details=None, refresh_lssrv=None, **kwargs) -> int:
    """Create the wx Jobs workspace; callbacks are service adapters, never UI IO."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    if refresh_sacct is None:
        refresh_sacct = kwargs.get("refresh_sacct") or kwargs.get("sacct")
    if show_job_details is None:
        show_job_details = kwargs.get("show_job_details") or kwargs.get("show_details") or kwargs.get("scontrol")
    if refresh_lssrv is None:
        refresh_lssrv = kwargs.get("refresh_lssrv") or kwargs.get("lssrv")
    _build_jobs(parent, model, list_jobs=list_jobs, read_output=read_output, cancel=cancel, lifecycle=lifecycle, final_state=final_state, generation=generation, embedded=False, refresh_sacct=refresh_sacct, show_job_details=show_job_details, refresh_lssrv=refresh_lssrv, **kwargs)
    return wx.ID_OK


__all__ = ["DetachedOutput", "WxJobsModel", "clean_output", "show_job_output", "show_jobs", "build_jobs_panel"]
